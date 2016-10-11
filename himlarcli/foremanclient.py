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

    def get_compute_resources(self):
        resources = self.foreman.index_computeresources()
        found_resources = dict({})
        for r in resources['results']:
            found_resources[r['name']] = r['id']
        return found_resources

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

    def create_node(self, name, node_data, region, dry_run=False):
        if self.get_host(name):
            self.logger.debug('=> node %s found, dropping create' % name)
            return
        found_resources = self.get_compute_resources()
        host = dict()
        host['name'] = name
        host['build'] = self.__get_node_data('build', node_data, '1')
        host['hostgroup_id'] = self.__get_node_data('hostgroup', node_data, '1')
        host['compute_profile_id'] = self.__get_node_data('compute_profile', node_data, '1')
        if 'mac' in node_data:
            host['mac'] = node_data['mac']
        if 'compute_resource' in node_data:
            compute_resource = '%s-%s' % (region, node_data['compute_resource'])
            if compute_resource in found_resources:
                host['compute_resource_id'] = found_resources[compute_resource]
            else:
                self.logger.critical('=> compute resource %s not found' % compute_resource)
                return
        elif 'mac' not in node_data:
            self.logger.critical('=> mac or compute resource are mandatory for %s' % name)
            return
        if not dry_run:
            result = self.foreman.create_hosts(host)
            if 'mac' not in node_data:
                self.foreman.hosts.power(id=result['name'], power_action='start')
            self.logger.debug('=> create host %s' % result)
        else:
            self.logger.debug('=> dry run: host config %s' % host)

    def __set_host(self, host):
        if not host:
            self.host = None
            return
        domain = self.config.get('openstack', 'domain')
        if domain and not '.' in host:
            self.logger.debug("=> prepend %s to %s" % (domain, host))
            host = host + '.' + domain
        return host

    def __get_node_data(self, var, node_data, default=None):
        if var in node_data:
            return node_data[var]
        else:
            return default

    def _print_attr():
        attr = self.foreman.__dict__
        for a in attr:
            print a
