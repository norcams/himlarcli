import os
import sys
import ConfigParser
import unicodedata
from keystoneclient.auth.identity import v3
from keystoneauth1 import session
from himlarcli import utils
from abc import ABCMeta, abstractmethod


class Client(object):

    """ Constant used to mark a class as region aware """
    USE_REGION = False

    __metaclass__ = ABCMeta
    region = None

    def __init__(self, config_path, debug, log=None, region=None):
        self.config = self.load_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: {}'.format(self.config_path))
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

    def get_config(self, section, option, default=None):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s'
                              % (section, option))
        except ConfigParser.NoSectionError:
            self.logger.debug('=> config file missing section %s' % section)
        return default

    def load_config(self, config_path):
        """ The config file will be loaded from the path given with the -c
            option path when running the script. If no -c option given it will
            also look for config.ini in:
                - local himlarcli root
                - /etc/himlarcli/
            If no config is found it will exit.
        """
        if config_path and not os.path.isfile(config_path):
            self.log_error("Could not find config file: {}".format(config_path), 1)
        elif not config_path:
            self.config_path = None
            local_config = utils.get_abs_path('config.ini')
            etc_config = '/etc/himlarcli/config.ini'
            if os.path.isfile(local_config):
                self.config_path = local_config
            else:
                if os.path.isfile(etc_config):
                    self.config_path = etc_config
            if not self.config_path:
                msg = "Config file not found in default locations:\n  {}\n  {}"
                self.log_error(msg.format(local_config, etc_config), 1)
        else:
            self.config_path = config_path
        return utils.get_config(self.config_path)

    def get_logger(self):
        """
            Return logger object
            :rtype: logging.Logger
        """
        return self.logger

    def debug_log(self, msg):
        prefix = '=> DRY-RUN:' if self.dry_run else '=>'
        self.logger.debug('%s %s', prefix, msg)

    def log_dry_run(self, function, **kwargs):
        if self.dry_run:
            output = '=> DRY-RUN %s: %s' % (function, kwargs)
            self.logger.debug(output)

    def get_fqdn(self, hostname):
        if not hostname:
            return None
        if '.' in hostname:
            return hostname
        domain = self.get_config('openstack', 'domain')
        return hostname + '.' + domain

    @staticmethod
    def get_attr(obj, attr):
        """
        Return attribute from object. This will work when attr are both
        attribute of object or keys of dict.
        """
        if isinstance(obj, dict) and attr in obj:
            return obj[attr]
        elif not isinstance(obj, dict) and hasattr(obj, attr):
            return getattr(obj, attr)
        return None

    @staticmethod
    def get_dict(obj):
        """
        Return a dict used for the output parser. This can be used both on
        dicts and openstack objects.
        """
        if isinstance(obj, dict):
            return obj
        elif hasattr(obj, 'to_dict'):
            return getattr(obj, 'to_dict')()
        else:
            return dict()

    @staticmethod
    def convert_ascii(text, format='replace'):
        """ Convert string to acsci.
            :param: format: replace (with ?) or ignore non-ascii characters
            version: 2019-10
        """
        if not text:
            return text
        text_unicode = unicode(text, 'utf-8') if  isinstance(text, str) else text
        text_normalize = unicodedata.normalize('NFKD', text_unicode)
        return text_normalize.encode('ascii', format)

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write("%s\n" % msg)
        if code > 0:
            sys.exit(code)

    # protected method
    def _get_client(self, client_class, region=None):
        """ Use to get an instance of a different client than the one calling
            version: 2019-11
            :param: client_class: the class of the client """
        class_without_region = ['Keystone', 'Designate']
        if not region:
            region = self.region
        if client_class.USE_REGION:
            client = client_class(config_path=self.config_path,
                                  debug=self.debug,
                                  log=self.logger,
                                  region=region)
        else:
            client = client_class(config_path=self.config_path,
                                  debug=self.debug,
                                  log=self.logger)
        client.set_dry_run(self.dry_run)
        return client
