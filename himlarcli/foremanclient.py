import ConfigParser
import warnings
from foreman.client import Foreman
import utils

class Client(object):

    def __init__(self, config_path, debug=False, version='1', log=None):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        config = self.config._sections['foreman']
        self.logger.debug('=> config file: %s' % config_path)
        self.logger.debug('=> foreman url: %s' % config['url'])

        self.foreman = Foreman(config['url'],
                               (config['user'], config['password']),
                               api_version=2,
                               version=version,
                               verify=False)
    def get_client(self):
        return self.foreman

    def get_host(self, host):
        host = self.__set_host(host)
        return self.foreman.show_hosts(id=host)

    def set_host_build(self, host, build=True):
        host = self.__set_host(host)
        if len(self.foreman.show_hosts(id=host)) > 0:
            self.foreman.update_hosts(id=host, host={'build': build})

    def get_hosts(self, search=None):
      hosts = self.foreman.index_hosts()
      self.logger.debug("=> fetch %s page(s) with a total of %s hosts" %
          (hosts['page'], hosts['total']))
      return hosts

    def create_host(self, host):
        if 'name' not in host:
            self.logger.critical('host dict missing name')
            return
        self.logger.debug('=> create new host %s' % host['name'])
        result = self.foreman.create_host(host)
        self.logger.debug('=> host created: %s' % result)

    def __set_host(self, host):
        if not host:
            self.host = None
            return
        domain = self.config.get('openstack', 'domain')
        if domain and not '.' in host:
            self.logger.debug("=> prepend %s to %s" % (domain, host))
            host = host + '.' + domain
        return host

    def _print_attr():
        attr = self.foreman.__dict__
        for a in attr:
            print a
