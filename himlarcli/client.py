import sys
import os.path
import ConfigParser
import logging
import utils
from state import State
from keystoneclient.auth.identity import v3
from keystoneclient import session
from novaclient import client
from abc import ABCMeta, abstractmethod


class Client(object):

    __metaclass__ = ABCMeta

    def __init__(self, config_path, debug, log=None):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.debug = debug

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

    def get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError as e:
            self.logger.debug('=> config file section [%s] missing option %s'
                               % (section, option))
        except ConfigParser.NoSectionError as e:
            self.logger.debug('=> config file missing section %s' % section)
        return None

    def get_logger(self):
        return self.logger

    def log(self, msg):
        print "client.log is depricated"
        self.logger.debug(msg)
