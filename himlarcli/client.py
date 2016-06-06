import sys
import os.path
import ConfigParser
import logger
from state import State
from keystoneclient.auth.identity import v3
from keystoneclient import session
from novaclient import client
from abc import ABCMeta, abstractmethod


class Client(object):

    __metaclass__ = ABCMeta

    def __init__(self, config_path, debug, log=None):
        if log:
            self.logger = log
        else:
            self.logger = logger.setup_logger(__name__, debug)

        if not os.path.isfile(config_path):
             self.logger.critical("Could not find config file: %s" %config_path)
             sys.exit(1)
        self.debug = debug

        self.config = ConfigParser.ConfigParser()
        self.config.read(config_path)
        try:
            openstack = self.config._sections['openstack']
        except KeyError as e:
            self.logger.exception('missing [openstack]')
            self.logger.critical('Could not find section [openstack] in %s', config_path)
            sys.exit(1)
        auth = v3.Password(auth_url=openstack['auth_url'],
                           username=openstack['username'],
                           password=openstack['password'],
                           project_name=openstack['project_name'],
                           user_domain_name=openstack['default_domain'],
                           project_domain_name=openstack['default_domain'])

        if 'keystone_cachain' in openstack:
            self.sess = session.Session(auth=auth,
                                        verify=openstack['keystone_cachain'])
        else:
            self.sess = session.Session(auth=auth)

        self.state = State(config_path, debug, log=self.logger)


    @abstractmethod
    def get_client(self):
        pass

    def get_logger(self):
        return logger

    def log(self, msg):
        self.logger.debug(msg)
