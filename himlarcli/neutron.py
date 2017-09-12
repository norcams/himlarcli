from himlarcli.client import Client
from neutronclient.v2_0.client import Client as neutronclient

class Neutron(Client):

    def __init__(self, config_path, debug=False, log=None, region=None):
        super(Neutron, self).__init__(config_path, debug, log, region)
        self.logger.debug('=> init neutron client for region %s' % self.region)
        self.client = neutronclient(session=self.sess,
                                    region_name=self.region)

    def get_client(self):
        return self.client

    def get_quota_class(self, class_name='default'):
        """ Quota class are not used by neutron. This function only follow the
            structure in functions for nova and cinder. """
        quota = self.client.show_quota(project_id=class_name)
        if 'quota' in quota:
            return quota['quota']
        return None

    def update_quota_class(self, class_name='default', updates=None):
        """ Quota class are not used by neutron. This function only follow the
            structure in functions for nova and cinder. """
        if not updates:
            updates = {}
        body = dict({'quota': updates})
        return self.client.update_quota(project_id=class_name, body=body)
