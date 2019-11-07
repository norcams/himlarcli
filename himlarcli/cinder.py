from himlarcli.client import Client
from cinderclient import client as cinderclient
from cinderclient.api_versions import APIVersion
from cinderclient import exceptions

class Cinder(Client):

    version = 2
    service_type = 'volumev3'

    def __init__(self, config_path, debug=False, log=None, region=None):
        """ Create a new cinder client to manaage volumes
        `**config_path`` path to ini file with config
        """
        super(Cinder, self).__init__(config_path, debug, log, region)
        version = self.get_config('openstack', 'volume_api_version', '3.50')
        self.debug_log('using cinder volume api_version %s' % version)
        self.client = cinderclient.Client(APIVersion(version),
                                        session=self.sess,
                                        service_type=self.service_type,
                                        region_name=self.region)


    def get_client(self):
        return self.client

    def get_volumes(self, detailed=False, search_opts=None):
        """ Return all or project volumes
            version: 2019-09 """
        volumes = self.__get_volumes(detailed=detailed, search_opts=search_opts)
        return volumes

    def get_volume_types(self):
        return self.client.volume_types.list()

    def get_pools(self, detail=True, search_opts=None):
        """ Return the volume pools """
        # NOTE(raykrist): all_tenants not working (2019-07-08)
        if not search_opts:
            search_opts = {'all_tenants': 0}
        elif 'all_tenants' not in search_opts:
            search_opts.update({'all_tenants': 0})
        return self.client.volumes.get_pools(detail=detail, search_opts=search_opts)

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

    def get_quota(self, project_id, usage=False):
        """ Get project quotas for volume services with current usage options
            version: 2019-7 """
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


    def __get_volumes(self, detailed=False, search_opts=None):
        if not search_opts:
            search_opts = dict(all_tenants=1)
        elif 'all_tenants' not in search_opts:
            search_opts['all_tenants'] = 1
        try:
            volumes = self.client.volumes.list(detailed=detailed,
                                               search_opts=search_opts)
        except exceptions.ClientException as e:
            self.log_error(e)
            return None
        return volumes
