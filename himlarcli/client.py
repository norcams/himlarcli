import sys
import ConfigParser
from keystoneclient.auth.identity import v3
from keystoneclient import session
from himlarcli import utils
from abc import ABCMeta, abstractmethod


class Client(object):

    __metaclass__ = ABCMeta
    region = None

    def __init__(self, config_path, debug, log=None, region=None):
        self.config_path = config_path
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.debug = debug
        self.dry_run = False

        openstack = self.get_config_section('openstack')
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

        if region:
            self.region = region
        else:
            self.region = self.get_config('openstack', 'region')
        #self.state = State(config_path, debug, log=self.logger)


    @abstractmethod
    def get_client(self):
        pass

    def set_dry_run(self, dry_run):
        self.logger.debug('=> set dry_run to %s in %s' % (dry_run, type(self).__name__))
        self.dry_run = True if dry_run else False

    def get_region(self):
        return self.get_config('openstack', 'region')

    def get_config_section(self, section):
        try:
            openstack = self.config.items(section)
        except ConfigParser.NoSectionError:
            self.logger.exception('missing [%s]' % section)
            self.logger.critical('Could not find section [%s] in %s', section, self.config_path)
            sys.exit(1)
        return dict(openstack)

    def get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s'
                              % (section, option))
        except ConfigParser.NoSectionError:
            self.logger.debug('=> config file missing section %s' % section)
        return None

    def get_logger(self):
        return self.logger

    def log(self, msg):
        print "client.log is depricated"
        self.logger.debug(msg)

    def log_dry_run(self, function, **kwargs):
        if self.dry_run:
            output = '=> DRY-RUN %s: %s' % (function, kwargs)
            self.logger.debug(output)

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write("%s\n" % msg)
        if code > 0:
            sys.exit(code)
