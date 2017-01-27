from client import Client
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient
from cinderclient import client as cinderclient
from novaclient.exceptions import NotFound
from datetime import datetime, date
import urllib2
import json
import pprint
import time


class Cinder(Client):

    version = 2
    service_type = 'volumev2'

    def __init__(self, config_path, debug=False, log=None, region=None):
        """ Create a new cinder client to manaage volumes
        `**config_path`` path to ini file with config
        """
        super(Cinder,self).__init__(config_path, debug, log, region)
        self.client = cinderclient.Client(self.version,
                                          session=self.sess,
                                          service_type=self.service_type,
                                          region_name=self.region)

    def get_client(self):
        return self.client

    def list_quota(self, project_id, usage=False):
        return self.client.quotas.get(tenant_id=project_id, usage=usage)

    def update_quota_class(self, class_name='default', updates={}):
        return self.client.quota_classes.update(class_name, **updates)

    def get_quota_class(self, class_name='default'):
        return self.client.quota_classes.get(class_name)
