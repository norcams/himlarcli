from himlarcli.client import Client
import sys
import ConfigParser
from foreman.client import Foreman
from himlarcli import utils

class ForemanClient(Client):

    def __init__(self, config_path, debug=False, version='1', log=None):
        super(ForemanClient, self).__init__(config_path, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        foreman_url = self.get_config('foreman', 'url')
        self.logger.debug('=> foreman url: %s' % foreman_url)
        foreman_user = self.get_config('foreman', 'user')
        foreman_password = self.get_config('foreman', 'password')
        self.foreman = Foreman(foreman_url,
                               (foreman_user, foreman_password),
                               api_version=2,
                               version=version,
                               verify=False)

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

    def get_config_section(self, section):
        try:
            openstack = self.config.items(section)
        except ConfigParser.NoSectionError:
            self.logger.debug('missing [%s]' % section)
            self.logger.debug('Could not find section [%s] in %s', section, self.config_path)
            sys.exit(1)
        return dict(openstack)

    def get_logger(self):
        return self.logger

    def get_client(self):
        return self.foreman

    def get_compute_resources(self):
        resources = self.foreman.index_computeresources()
        found_resources = dict({})
        for r in resources['results']:
            found_resources[r['name']] = r['id']
        return found_resources

    def get_compute_profiles(self):
        profiles = self.foreman.index_computeprofiles()
        found_profiles = dict({})
        for p in profiles['results']:
            found_profiles[p['name']] = p['id']
        return found_profiles

    def get_host(self, host):
        host = self.__set_host(host)
        return self.foreman.show_hosts(id=host)

    def get_fact(self, host, fact):
        host = self.__set_host(host)
        facts = self.get_facts(host)
        fact = facts['results'][host][fact]
        return fact

    def get_facts(self, host_id):
        host = self.__set_host(host_id)
        return self.foreman.hosts.fact_values_index(host_id=host, per_page=10000)

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
            self.logger.debug('host dict missing name')
            return
        self.logger.debug('=> create new host %s' % host['name'])
        result = self.foreman.create_host(host)
        self.logger.debug('=> host created: %s' % result)

    def create_node(self, name, node_data, region):
        if self.get_host(name):
            self.logger.debug('=> node %s found, dropping create' % name)
            return
        found_resources = self.get_compute_resources()
        host = dict()
        host['name'] = name
        host['build'] = self.__get_node_data('build', node_data, '1')
        host['hostgroup_id'] = self.__get_node_data('hostgroup', node_data, '1')
        host['compute_profile_id'] = self.__get_node_data('compute_profile', node_data, '1')
        host['interfaces_attributes'] = self.__get_node_data(
            'interfaces_attributes', node_data, {})
        host['compute_attributes'] = self.__get_node_data(
            'compute_attributes', node_data, {})
        host['host_parameters_attributes'] = self.__get_node_data(
            'host_parameters_attributes', node_data, {})
        if 'mac' in node_data:
            host['mac'] = node_data['mac']
        if 'compute_resource' in node_data:
            compute_resource = '%s-%s' % (region, node_data['compute_resource'])
            if compute_resource in found_resources:
                host['compute_resource_id'] = found_resources[compute_resource]
            else:
                self.logger.debug('=> compute resource %s not found' % compute_resource)
                return
        elif 'mac' not in node_data:
            self.logger.debug('=> mac or compute resource are mandatory for %s' % name)
            return
        if not self.dry_run:
            result = self.foreman.create_hosts(host)
            if not result:
                self.log_error('Could not create host. Check production.log on foreman host!')
                return
            if 'mac' not in node_data:
                self.foreman.hosts.power(id=result['name'], power_action='start')
            self.logger.debug('=> create host %s' % result)
        else:
            self.logger.debug('=> dry run: host config %s' % host)

    def delete_node(self, host):
        host = self.__set_host(host)
        if not self.dry_run:
            result = self.foreman.destroy_hosts(host)
            if not result:
                self.log_error('Could not delete host.')
                return
            self.logger.debug('=> deleted node %s' % host)
        else:
            self.logger.debug('=> dry run: deleted node %s' % host)

    def __set_host(self, host):
        if not host:
            self.host = None
            return
        domain = self.config.get('openstack', 'domain')
        if domain and not '.' in host:
            self.logger.debug("=> prepend %s to %s" % (domain, host))
            host = host + '.' + domain
        return host

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write("%s\n" % msg)
        if code > 0:
            sys.exit(code)

    @staticmethod
    def __get_node_data(var, node_data, default=None):
        if var in node_data:
            return node_data[var]
        else:
            return default
