import sys
import logging
import logging.config
import warnings
import yaml
import ConfigParser
from keystoneclient.auth.identity import v3
from keystoneclient import session
from novaclient import client
from abc import ABCMeta, abstractmethod


class Client(object):

    __metaclass__ = ABCMeta

    def __init__(self, config_path, debug):
        self.debug = debug
        self.__setup_logger(debug)
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

    @abstractmethod
    def get_client(self):
        pass

    def log(self, msg):
        self.logger.debug(msg)

    def __setup_logger(self, debug):
        with open("logging.yaml", 'r') as stream:
            try:
                config = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        if config:
            logging.config.dictConfig(config)
        self.logger = logging.getLogger(__name__)
        logging.captureWarnings(True)
        # If debug add verbose console logger only to our logger
        if (debug):
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            self.logger.addHandler(ch)
