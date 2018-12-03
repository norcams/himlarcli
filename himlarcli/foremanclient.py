from himlarcli.client import Client
import sys
import ConfigParser
import requests
import json
from himlarcli import utils

class ForemanClient(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(ForemanClient, self).__init__(config_path, debug, log)
        self.foreman_url = self.get_config('foreman', 'url')
        self.logger.debug('=> config file: %s' % config_path)
        self.logger.debug('=> foreman url: %s' % self.foreman_url)
        foreman_user = self.get_config('foreman', 'user')
        foreman_password = self.get_config('foreman', 'password')
        self.api_version = '2'
        self.session = requests.Session()
        self.session.auth = (foreman_user, foreman_password)
        self.session.verify = False
        self.session.headers.update(
            {
                'Accept': 'application/json; version=2',
                'Content-type': 'application/json'
            })

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
        return self.client

    def get_compute_resources(self):
        resource = '/api/compute_resources'
        resources = self._get(resource, per_page='10000')
        found_resources = dict({})
        for r in resources['results']:
            found_resources[r['name']] = r['id']
        return found_resources

    def create_compute_resources(self, data):
        resource = '/api/compute_resources'
        res = self._post(resource, data)
        return res

    def update_compute_resources(self, name, data):
        resource = '/api/compute_resources/%s' % name
        res = self._put(resource, data)
        return res

    def create_compute_attributes(self, profile_id, resource_id, data):
        resource = '/api/compute_profiles/%s/compute_resources/%s/compute_attributes' % (profile_id, resource_id)
        res = self._post(resource, data)
        return res

    def update_compute_attributes(self, profile_id, resource_id, attr_id, data):
        resource = '/api/compute_profiles/%s/compute_resources/%s/compute_attributes/%s' % (profile_id, resource_id, attr_id)
        res = self._put(resource, data)
        return res

    def show_compute_profile(self, name):
        resource = '/api/compute_profiles/%s' % name
        res = self._get(resource)
        return res

    def get_host(self, host):
        host = self.__set_host(host)
        resource = "/api/hosts/%s" % host
        return self._get(resource)

    def get_fact(self, host, fact):
        host = self.__set_host(host)
        facts = self.get_facts(host)
        if facts['results']:
            fact = facts['results'][host][fact]
            return fact
        else:
            return None

    def get_facts(self, host):
        host = self.__set_host(host)
        resource = "/api/hosts/%s/facts" % host
        return self._get(resource, per_page='10000')

    def set_host_build(self, name, build=True):
        host = dict()
        host['name'] = self.__set_host(name)
        host['build'] = build
        resource = '/api/hosts/%s' % name
        if len(self.get_host(name)) > 0:
            self._put(resource, host)

    def get_hosts(self, search=None):
        resource = '/api/hosts'
        return self._do_get(resource, per_page='10000', search=search)

    def power_on(self, hostname):
        resource = '/api/hosts/%s/power' % hostname
        self.logger.debug('=> Power on %s' % hostname)
        self._do_put(resource, power_action='start')

    def create_host(self, host):
        if 'name' not in host:
            self.logger.debug('host dict missing name')
            return
        self.logger.debug('=> create new host %s' % host['name'])
        resource = '/api/hosts'
        res = self._post(resource, host)
        if type(res) is dict:
            return res
        else:
            return None

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
        print host
        if not self.dry_run:
            result = self.create_host(host)
            if not result:
                self.log_error('Could not create host. Check production.log on foreman host!')
                return
            if 'mac' not in node_data:
                self.power_on(host['name'])
            self.logger.debug('=> create host %s' % result)
        else:
            self.logger.debug('=> dry run: host config %s' % host)

    def delete_node(self, host):
        host = self.__set_host(host)
        if not self.dry_run:
            resource = "/api/hosts/%s" % host
            result = self._delete(resource)
            if not result:
                self.log_error('=> could not delete node %s' % host)
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

    def _get(self, url, **kwargs):
        """
        :param url: relative url to resource
        :param kwargs: parameters for the api call
        """
        res = self.session.get(
            '%s%s' % (self.foreman_url, url),
            params=kwargs
        )
        return self._process_request_result(res)

    def _post(self, url, data):
        """
        :param url: relative url to resource
        :param data: parameters for the api call
        """
        data = json.dumps(data)
        res = self.session.post(
            '%s%s' % (self.foreman_url, url),
            data=data
        )
        return self._process_request_result(res)

    def _put(self, url, data):
        """
        :param url: relative url to resource
        :param kwargs: parameters for the api call
        """
        data = json.dumps(data)
        res = self.session.put(
            '%s%s' % (self.foreman_url, url),
            data=data
        )
        return self._process_request_result(res)

    def _delete(self, url):
        """
        :param url: relative url to resource
        :param kwargs: parameters for the api call
        """
        res = self.session.delete(
            '%s%s' % (self.foreman_url, url),
        )
        return self._process_request_result(res)

    def _process_request_result(self, res):
        if res.status_code < 200 or res.status_code >= 300:
            if res.status_code == 404:
                return []
            elif res.status_code == 406:
                self.log_error('=> API returned 406: %s' % res)
            self.log_error('Something went wrong: %s' % res)
        try:
            return res.json()
        except ValueError:
            return res.text

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
