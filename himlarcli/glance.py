import itertools
from himlarcli.client import Client
from glanceclient import Client as glclient
from glanceclient import exc
import sys

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

    """ Get images.
    To filter use filters dict with key value pairs.
    E.G. get_images(filters={'key': 'value'}) """
    def get_images(self, **kwargs):
        return self.client.images.list(**kwargs)

    def find_image(self, **kwargs):
        """ Same as get_images but return a list.
            This should only be used for small sets!
            This can be achieved by using limit=1 in filters """
        images = self.client.images.list(**kwargs)
        return list(images)

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
        self.logger.debug('=> create new image %s' % kwargs['name'])
        self.image = self.client.images.create(**kwargs)
        self.upload_image(source_path)
        return self.image

    def delete_private_images(self, project_id):
        images = self.get_images(filters={'owner': project_id})
        for image in images:
            self.delete_image(image.id)

    def delete_image(self, image_id):
        if not self.image and not image_id:
            self.logger.critical('Image must exist before deletion.')
            return
        if not image_id:
            image_id = self.image.id
        self.debug_log('image delete %s' % image_id)
        if not self.dry_run:
            self.client.images.delete(image_id)

    def update_image(self, name, image_id=None, **kwargs):
        if not self.image and not image_id:
            self.logger.debug('=> image not found %s' % name)
            if name:
                self.get_image(name)
            else:
                self.logger.critical('Image must exist before upload.')
                sys.exit(1)
        if not image_id:
            image_id = self.image.id
        self.client.images.update(image_id=image_id, name=name, **kwargs)

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

    def deactivate(self, name=None, image_id=None):
        if not self.image and not image_id:
            self.logger.debug('=> image not found %s' % name)
            if name:
                self.get_image(name)
            else:
                self.logger.critical('Image must exist to deactivate.')
                sys.exit(1)
        if not image_id:
            image_id = self.image.id
        self.client.images.deactivate(image_id)
        self.logger.debug('=> deactivate image id %s' % image_id)

    def reactivate(self, image_id):
        try:
            self.logger.debug('=> reactivate image id %s' % image_id)
            self.client.images.reactivate(image_id)
        except exc.HTTPNotFound:
            self.logger.error('=> image id %s not found' % image_id)

    def upload_image(self, source_path, name=None):
        if not self.image:
            self.logger.debug('=> image not found %s' % name)
            if name:
                self.get_image(name)
            else:
                self.logger.critical('Image must exist before upload.')
                sys.exit(1)
        try:
            self.client.images.upload(self.image.id, open(source_path, 'rb'))
            self.logger.debug('=> upload new image %s' % source_path)
        except BaseException as e:
            print e
            self.logger.critical('Upload of %s failed' % self.image.name)
            sys.exit(1)

    @staticmethod
    def find_optimal_flavor(image, flavors):
        # If the flavors are sorted by size this will work
        for flavor in flavors:
            if flavor.ram >= image['min_ram'] and flavor.disk >= image['min_disk']:
                return flavor
        return None

    def __get_images(self):
        self.images = self.client.images.list()
