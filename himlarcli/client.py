import ConfigParser
from keystoneclient.auth.identity import v3
from keystoneclient import session
from novaclient import client
from abc import ABCMeta, abstractmethod


class Client(object):

    __metaclass__ = ABCMeta

    def __init__(self, config_path):
        self.config = ConfigParser.ConfigParser()
        self.config.read(config_path)
        openstack = self.config._sections['openstack']
        auth = v3.Password(auth_url=openstack['auth_url'],
                           username=openstack['username'],
                           password=openstack['password'],
                           project_name=openstack['project_name'],
                           user_domain_name=openstack['default_domain'],
                           project_domain_name=openstack['default_domain'])

        if openstack['keystone_cachain']:
            self.sess = session.Session(auth=auth,
                                        verify=openstack['keystone_cachain'])
        else:
            self.sess = session.Session(auth=auth)

    @abstractmethod
    def get_client(self):
        pass
