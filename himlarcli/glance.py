import itertools
from himlarcli.client import Client
from glanceclient import Client as glclient
from glanceclient import exc

class Glance(Client):

    """ Constant used to mark a class as region aware """
    USE_REGION = True

    version = 2
    """ All images """
    images = None
    """ Active image """
    image = None

    def __init__(self, config_path, debug=False, log=None, region=None):
        super(Glance, self).__init__(config_path, debug, log, region)
        self.logger.debug('=> init glance client verion %s for region %s' %
                          (self.version, self.region))
        self.client = glclient(self.version,
                               session=self.sess,
                               region_name=self.region)

    def get_client(self):
        return self.client

    def get_image_by_id(self, image_id):
        try:
            image = self.client.images.get(image_id)
        except exc.HTTPNotFound:
            image = None
            self.log_error('Image with ID %s not found!' % image_id)
        return image

    def get_images(self, **kwargs):
        """
            Get images.
            To filter use filters dict with key value pairs.
            E.G. get_images(filters={'key': 'value'})
        """
        return self.client.images.list(**kwargs)

    def find_image(self, **kwargs):
        """ Same as get_images but return a list.
            This should only be used for small sets!
            This can be achieved by using limit=1 in filters """
        result = self.client.images.list(**kwargs)
        try:
            images = list(result) if result else list()
            return images
        except exc.HTTPServiceUnavailable:
            self.log_error('Glance: Service Unavailable')
        return list()

    def get_image(self, name):
        """ depricated use find_image"""
        if not self.images:
            self.__get_images()
        # Make sure we loop a new generator from the start
        self.images, image_list = itertools.tee(self.images)
        for image in image_list:
            if name == image['name']:
                self.logger.debug('=> image found %s' % name)
                self.image = image
                return image
        self.logger.debug('=> image not found %s' % name)
        return None

    def create_image(self, source_path, **kwargs):
        if 'name' not in kwargs:
            self.log_error('image name missing!')
            return None
        self.debug_log('create new image {}'.format(kwargs['name']))
        image = None
        try:
            if not self.dry_run:
                image = self.client.images.create(**kwargs)
        except exc.HTTPServiceUnavailable as e:
            self.log_error(e)
        if image:
            self.__upload_image(source_path, image)
            return image
        return None

    def delete_private_images(self, project_id):
        images = self.find_image(filters={'owner': project_id})
        for image in images:
            self.delete_image(image.id)

    def delete_image(self, image_id):
        if not self.get_image_by_id(image_id):
            self.debug_log('deletion failed! not fond: {}'.format(image_id))
            return
        self.debug_log('delete image id {}'.format(image_id))
        try:
            if not self.dry_run:
                self.client.images.delete(image_id)
        except exc.HTTPServiceUnavailable as e:
            self.log_error(e)

    def update_image(self, name, image_id, **kwargs):
        if not self.get_image_by_id(image_id):
            self.debug_log('image not fond: {}'.format(name))
            return
        try:
            if not self.dry_run:
                self.client.images.update(image_id=image_id, name=name, **kwargs)
            updated_data = dict(kwargs)
            updated_data['name'] = name
            self.debug_log('update image: {}'.format(updated_data))
        except exc.HTTPServiceUnavailable as e:
            self.log_error(e)

    def get_image_access(self, image_id):
        try:
            members = self.client.image_members.list(image_id)
        except exc.HTTPServiceUnavailable as e:
            self.log_error(e)
        return members

    def set_image_access(self, image_id, project_id, action='grant'):
        if action not in ['grant', 'revoke']:
            self.debug_log('unknown image access action: {}'.format(action))
            return

        if action == 'grant':
            if self.__get_project_image_member(image_id, project_id):
                self.debug_log(('membership exsist: dropping grant for project '
                                + '{} on image {}').format(project_id, image_id))
                return
            if not self.dry_run:
                try:
                    self.client.image_members.create(image_id, project_id)
                    self.client.image_members.update(image_id, project_id, 'accepted')
                except exc.HTTPServiceUnavailable as e:
                    self.log_error(e)
            self.debug_log('grant access to project {} for image {}'.
                           format(project_id, image_id))
        elif action == 'revoke':
            if not self.__get_project_image_member(image_id, project_id):
                return
            if not self.dry_run:
                try:
                    self.client.image_members.delete(image_id, project_id)
                except exc.HTTPServiceUnavailable as e:
                    self.log_error(e)
            self.debug_log('revoke access to project {} for image {}'.
                           format(project_id, image_id))


    def set_access(self, image_id, project_id, action='create'):
        if action not in ['create', 'delete']:
            self.logger.warn('=> unknown action %s' % action)
            return
        members = self.client.image_members.list(image_id)
        found = False
        for member in members:
            if member.member_id == project_id:
                found = True
                continue
        if found and action == 'create':
            self.logger.debug('=> access to image %s allready exists' % image_id)
            return
        if not found and action == 'delete':
            self.logger.debug('=> no access to delete for image %s' % image_id)
            return
        if action == 'create':
            result = self.client.image_members.create(image_id, project_id)
            self.logger.debug('=> %s' % result)
            self.client.image_members.update(image_id, project_id, 'accepted')
        if action == 'delete':
            result = self.client.image_members.delete(image_id, project_id)
            self.logger.debug('=> %s' % result)

    def get_access(self, image_id):
        return self.client.image_members.list(image_id)

    def deactivate(self, image_id):
        if not self.get_image_by_id(image_id):
            self.debug_log('deactivation failed! not fond: {}'.format(image_id))
            return
        self.debug_log('deactivate image id {}'.format(image_id))
        try:
            if not self.dry_run:
                self.client.images.deactivate(image_id)
        except exc.HTTPServiceUnavailable as e:
            self.log_error(e)

    def reactivate(self, image_id):
        if not self.get_image_by_id(image_id):
            self.debug_log('reactiation failed! not fond: {}'.format(image_id))
            return
        self.debug_log('reactivate image id {}'.format(image_id))
        try:
            if not self.dry_run:
                self.client.images.reactivate(image_id)
        except exc.HTTPServiceUnavailable as e:
            self.log_error(e)

    def __upload_image(self, source_path, image):
        try:
            if not self.dry_run:
                self.client.images.upload(image.id, open(source_path, 'rb'))
            self.debug_log('upload new image %s' % source_path)
        except BaseException as e:
            print e
            self.log_error('Upload of {} failed'.format(image.name), 1)

    @staticmethod
    def find_optimal_flavor(image, flavors):
        # If the flavors are sorted by size this will work
        for flavor in flavors:
            if flavor.ram >= image['min_ram'] and flavor.disk >= image['min_disk']:
                return flavor
        return None

    def __get_project_image_member(self, image_id, project_id):
        members = self.client.image_members.list(image_id)
        for member in members:
            if member.member_id == project_id:
                return True
        return False

    def __get_images(self):
        self.images = self.client.images.list()
