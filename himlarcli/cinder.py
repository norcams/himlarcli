from himlarcli.client import Client
from cinderclient import client as cinderclient
from cinderclient import exceptions

class Cinder(Client):

    version = 2
    service_type = 'volumev2'

    def __init__(self, config_path, debug=False, log=None, region=None):
        """ Create a new cinder client to manaage volumes
        `**config_path`` path to ini file with config
        """
        super(Cinder, self).__init__(config_path, debug, log, region)
        self.client = cinderclient.Client(self.version,
                                          session=self.sess,
                                          service_type=self.service_type,
                                          region_name=self.region)

    def get_usage(self, project_id):
        return self.client.quotas.get(tenant_id=project_id, usage=True)

    def get_client(self):
        return self.client

    def update_quota(self, project_id, updates):
        """ Update project cinder quota
            version: 2 """
        dry_run_txt = 'DRY-RUN: ' if self.dry_run else ''
        self.logger.debug('=> %supdate quota for %s = %s' % (dry_run_txt, project_id, updates))
        result = None
        try:
            if not self.dry_run:
                result = self.client.quotas.update(tenant_id=project_id, **updates)
        except exceptions.NotFound as e:
            self.log_error(e)
        return result

    def list_quota(self, project_id, usage=False):
        result = self.client.quotas.get(tenant_id=project_id, usage=usage)
        if result:
            return result.to_dict()
        return dict()

    def update_quota_class(self, class_name='default', updates=None):
        if not updates:
            updates = {}
        return self.client.quota_classes.update(class_name, **updates)

    def get_quota_class(self, class_name='default'):
        return self.client.quota_classes.get(class_name)
