import ConfigParser
import warnings
from foreman.client import Foreman
import utils

class Client(object):

    def __init__(self, config_path, debug=False, version='1'):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug)
        config = self.config._sections['foreman']
        self.logger.debug('=> config file: %s' % config_path)
        self.logger.debug('=> foreman url: %s' % config['url'])

        self.foreman = Foreman(config['url'],
                               (config['user'], config['password']),
                               api_version=2,
                               version=version,
                               verify=False)

    def set_host_build(self, host, build=True):
        host = self.__set_host(host)
        if len(self.foreman.show_hosts(id=host)) > 0:
            self.foreman.update_hosts(id=host, host={'build': build})

    def get_hosts(self, search=None):
      hosts = self.foreman.index_hosts()
      self.logger.debug("=> fetch %s page(s) with a total of %s hosts" %
          (hosts['page'], hosts['total']))
      return hosts

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
