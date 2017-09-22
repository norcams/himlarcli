from himlarcli.client import Client
from neutronclient.v2_0.client import Client as neutronclient
from neutronclient.common import exceptions

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
        self.log_error('quota_class not defined for neutron', 0)
        return dict()

    def update_quota_class(self, class_name='default', updates=None):
        """ Quota class are not used by neutron. This function only follow the
            structure in functions for nova and cinder. """
        self.log_error('quota_class not defined for neutron', 0)
        return dict()

    def list_quota(self, project_id, usage=False):
        result = self.client.show_quota(project_id=project_id)
        if 'quota' in result:
            return result['quota']
        return dict()

    def update_quota(self, project_id, updates):
        """ Update project neutron quota
            version: 2 """
        dry_run_txt = 'DRY-RUN: ' if self.dry_run else ''
        self.logger.debug('=> %supdate quota for %s = %s' % (dry_run_txt, project_id, updates))
        result = None
        try:
            if not self.dry_run:
                result = self.client.update_quota(project_id=project_id, body={'quota': updates})
        except exceptions.NotFound as e:
            self.log_error(e)
        return result
