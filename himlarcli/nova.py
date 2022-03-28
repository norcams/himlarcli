from himlarcli.client import Client
from novaclient import client as novaclient
from novaclient.api_versions import APIVersion
import novaclient.exceptions as exceptions
from keystoneclient.v3 import client as keystoneclient
import keystoneauth1.exceptions as keyexc
from datetime import date, datetime, timedelta
import urllib2
import time

# pylint: disable=R0904

class Nova(Client):

    """ Constant used to mark a class as region aware """
    USE_REGION = True

    instances = dict()
    ksclient = None

    valid_objects = ['flavor', 'server']

    def __init__(self, config_path, debug=False, log=None, region=None):
        """ Create a new nova client to manaage a host
        `**host`` fqdn for the nova compute host
        `**config_path`` path to ini file with config
        """
        super(Nova, self).__init__(config_path, debug, log, region)
        version = self.get_config('openstack', 'compute_api_version')
        self.debug_log('using nova compute api_version %s' % version)
        self.client = novaclient.Client(APIVersion(version),
                                        session=self.sess,
                                        region_name=self.region)

    def get_keystone_client(self):
        """ Create a new keystone client if needed and then return the client """
        if not self.ksclient:
            self.ksclient = keystoneclient.Client(session=self.sess,
                                                  region_name=self.region)
        return self.ksclient


    def get_by_name(self, obj_type, obj_name, is_public=None):
        """
        Get valid openstack object by type and name.
        version: 2018-7
        """
        if obj_type not in self.valid_objects:
            self.logger.debug('=> %s is not a valid object type', obj_type)
            return
        try:
            return getattr(self.client, '%ss' % obj_type).find(
                name=obj_name,
                is_public=is_public)
        except novaclient.exceptions.NotFound:
            self.logger.debug('=> %s with name %s not found', obj_type, obj_name)

    def get_by_id(self, obj_type, obj_id):
        """ Get valid openstack object by type and id.
            version: 2 """
        if obj_type not in self.valid_objects:
            self.logger.debug('=> %s is not a valid object type', obj_type)
            return None
        try:
            result = getattr(self.client, '%ss' % obj_type).get(obj_id)
        except novaclient.exceptions.NotFound:
            self.logger.debug('=> %s with id %s not found', obj_type, obj_id)
            result = None
        return result

    def get_keypairs(self, user_id):
        """ Return all keypair for a user """
        return self.client.keypairs.list(user_id=user_id, marker=0, limit=50)

# =============================== SERVER ======================================

    def create_server(self, name, flavor, image_id, **kwargs):
        """ Create a server. Server will be crated by the user and project
            used in config.ini (default admin and openstack) """
        try:
            server = self.client.servers.create(name=name,
                                                flavor=flavor,
                                                image=image_id,
                                                **kwargs)
        except (exceptions.Conflict, exceptions.Forbidden) as e:
            self.log_error(e)
            server = None
        return server

# =============================== HOSTS =======================================
    def get_host(self, hostname, detailed=False):
        """
            Return hypervisor from hostname
            Version: 2018-1
            :rtype: novaclient.v2.hypervisors.Hypervisor
        """
        try:
            hosts = self.client.hypervisors.search(hostname)
        except novaclient.exceptions.NotFound as e:
            self.logger.warning('=> %s', e)
            return None
        for host in hosts:
            if host.hypervisor_hostname == hostname:
                if detailed:
                    return self.client.hypervisors.get(host.id)
                return host

    def get_hosts(self, detailed=True):
        """
            Return all hypervisor from all aggregates
            Version: 2018-1
            :rtype: novaclient.base.ListWithMeta
        """
        return self.client.hypervisors.list(detailed)

    def get_service(self, host, service='nova-compute'):
        return self.client.services.list(host=host, binary=service)

    def enable_host(self, name, service='nova-compute'):
        services = self.client.services.list(host=name, binary=service)
        for s in services:
            self.client.services.enable(s.id)
        self.logger.debug('=> enable %s services on host %s' % (service, name))

    def disable_host(self, name, service='nova-compute'):
        services = self.client.services.list(host=name, binary=service)
        for s in services:
            self.client.services.disable(s.id)
        self.logger.debug('=> disable %s services on host %s' % (service, name))

################################## AGGREGATE ##################################

    def move_host_aggregate(self, hostname, aggregate, remove_from_old=True):
        host = self.get_host(hostname)
        to_agg = self.get_aggregate(aggregate)
        if not host: return # host not found
        if not to_agg: return # aggregate not found
        if hostname in to_agg.hosts: return # host already in aggregate

        if host.status != 'enabled':
            if not self.dry_run: self.enable_host(hostname)
            enabled = True
        else: enabled = False

        if remove_from_old:
            aggregates = self.get_aggregates(False)
            for agg in aggregates:
                if hostname in agg.hosts:
                    if not self.dry_run: agg.remove_host(hostname)
                    self.logger.debug('=> remove host %s from aggregate %s',
                                      hostname, agg.name)
        if not self.dry_run:
            to_agg.add_host(hostname)
        self.logger.debug('=> add host %s to aggregate %s', hostname, to_agg.name)

        if enabled and not self.dry_run:
            self.disable_host(hostname)
        return True

    def get_filtered_aggregates(self, **kwargs):
        aggregates = self.client.aggregates.findall(**kwargs)
        return aggregates

    def get_aggregates(self, simple=True):
        aggregates = self.client.aggregates.list()
        if not simple:
            return aggregates
        agg_list = list()
        for aggregate in aggregates:
            agg_list.append(aggregate.name)
        return agg_list

    def get_aggregate(self, aggregate):
        """
            Return an aggregate
            Version: 2018-1
            :rtype: novaclient.v2.aggregates.Aggregate
        """
        try:
            aggregate = self.client.aggregates.find(name=aggregate)
        except novaclient.exceptions.NotFound as e:
            self.debug_log('{}: {}'.format(self.region, e))
            return None
        return aggregate

    def get_aggregate_hosts(self, aggregate, detailed=False):
        """
            Return all hypervisors/hosts from an aggregate
            Version: 2018-1
            :rtype: List
        """
        aggregate = self.__get_aggregate(aggregate)
        hosts = list()
        if not aggregate:
            return hosts
        for h in aggregate.hosts:
            hosts.append(self.get_host(h, detailed))
        return hosts

    def update_aggregate(self, aggregate, metadata):
        """
            Update aggregate metadata
            Version: 2020-9
        """
        aggregate = self.get_aggregate(aggregate)
        if not self.dry_run:
            self.client.aggregates.set_metadata(aggregate.id, metadata)

    def get_instances(self, aggregate=None, host=None, simple=False):
        if not aggregate:
            instances = self.__get_instances(host=host)
        else:
            agg = self.__get_aggregate(aggregate)
            if not agg or not hasattr(agg, 'hosts') or not agg.hosts:
                self.logger.debug('=> not hosts found in aggregate %s' % aggregate)
                instances = list()
            else:
                instances = list()
                for h in agg.hosts:
                    if host and host != h:
                        self.logger.debug('=> single host spesified. Drop %s in %s'
                                          % (h, aggregate))
                        continue
                    self.logger.debug('=> hosts %s found in aggregate %s' % (h, aggregate))
                    instances += self.__get_instances(h)
        host_txt = ' (host=%s)' % host if host else ''
        self.logger.debug("=> found %s instances in %s%s" % (len(instances), aggregate, host_txt))
        if not simple:
            return instances
        else:
            instance_list = list()
            for i in instances:
                instance_list.append(i.name)
            return instance_list

    def get_users(self, aggregate=None, simple=False):
        self.get_keystone_client()
        instances = self.get_instances(aggregate)
        emails = set() if simple else list()
        for i in instances:
            try:
                user = self.ksclient.users.get(i.user_id)
            except keyexc.http.NotFound:
                self.logger.error("=> user for instance %s (%s) not found ", i.id, i.name)
                continue
            self.logger.debug('=> found user %s for instance %s' % (user.name, i.name))
            if not simple:
                emails.append(user)
            elif "@" in user.name:
                emails.add(user.name.lower())
                self.logger.debug("=> add %s to user list" % user.name)
        return emails

    def get_all_aggregate_hosts(self):
        aggregates = self.client.aggregates.list()
        hosts = dict()
        for aggregate in aggregates:
            if not hasattr(aggregate, 'hosts'):
                continue
            for h in aggregate.hosts:
                hosts[h] = aggregate.name
        return hosts

    def get_availability_zones(self):
        az = self.client.availability_zones.list()
        return az

################################## INSTANCES ##################################

    def get_all_instances(self, search_opts=None):
        if not search_opts:
            search_opts = {'all_tenants': 1}
        elif 'all_tenants' not in search_opts:
            search_opts.update({'all_tenants': 1})
        return self.__get_all_instances(search_opts)

    def get_project_instances(self, project_id, deleted=False):
        search_opts = dict(tenant_id=project_id, all_tenants=1)
        if deleted:
            search_opts['deleted'] = 1
        instances = self.__get_all_instances(search_opts=search_opts)
        self.logger.debug('=> found %s instances for project %s' % (len(instances), project_id))
        return instances

    def stop_instance(self, instance):
        """
            Wrapper to stop an instance
            Version: 2020-09
        """
        if instance.status == 'ACTIVE' and not self.dry_run:
            try:
                instance.stop()
            except novaclient.exceptions.Conflict as e:
                self.log_error(e)
        if instance.status == 'ACTIVE':
            self.debug_log('stop instance {}'.format(instance.id))

    def start_instance(self, instance):
        """
            Wrapper to start an instance
            Version: 2020-09
        """
        if instance.status == 'SHUTOFF' and not self.dry_run:
            try:
                instance.start()
            except novaclient.exceptions.Conflict as e:
                self.log_error(e)
        if instance.status == 'SHUTOFF':
            self.debug_log('start instance {}'.format(instance.id))

    def stop_project_instances(self, project, dry_run=False):
        """
            Stop all instances in a project
            Version: 2022-03
        """
        search_opts = dict(tenant_id=project.id, all_tenants=1)
        instances = self.__get_all_instances(search_opts=search_opts)
        if not instances:
            self.logger.debug('=> no instances found for project %s' % project.name)
            return
        for i in instances:
            if not dry_run:
                if i.status == 'ACTIVE' and not self.dry_run:
                    try:
                        i.stop()
                    except novaclient.exceptions.Conflict as e:
                        self.log_error(e)
                if i.status == 'ACTIVE':
                    self.debug_log('stop instance {}'.format(i.id))
            else:
                self.logger.debug('=> DRY-RUN: stop instance %s (%s)' % (i.name, project.name))

    def delete_project_instances(self, project, dry_run=False):
        """ Delete all instances for a project """
        search_opts = dict(tenant_id=project.id, all_tenants=1)
        instances = self.__get_all_instances(search_opts=search_opts)
        if not instances:
            self.logger.debug('=> no instances found for project %s' % project.name)
            return
        for i in instances:
            if not dry_run:
                self.logger.debug('=> delete instance %s (%s)' % (i.name, project.name))
                i.delete()
                time.sleep(5)
            else:
                self.logger.debug('=> DRY-RUN: delete instance %s (%s)' % (i.name, project.name))

    def delete_instance(self, instance):
        """
            Wrapper for delete instance
            Version: 2021-03
        """
        self.debug_log('Delete instance with id %s' % (instance.id))
        try:
            if not self.dry_run:
                instance.delete()
        except Exception as e:
            self.debug_log('failed to delete instance {}'.format(instance.id))
            self.log_error(e)
        #time.sleep(5)

#################################### QUOTA ####################################

    def get_quota(self, project_id, detail=False):
        """ Get a projects nova quota.

            :return: a dictionary with quota information
        """
        # This require novaclient version > mitaka
        result = self.client.quotas.get(tenant_id=project_id, detail=detail)
        if result:
            return result.to_dict()
        return dict()

    def set_quota(self, project_id, quota):
        self.logger.debug('=> quota set to %s' % quota)
        self.client.quotas.update(project_id, **quota)

    def update_quota(self, project_id, updates):
        """ Update project nova quota
            version: 2 """
        dry_run_txt = 'DRY-RUN: ' if self.dry_run else ''
        self.logger.debug('=> %supdate quota for %s = %s' % (dry_run_txt, project_id, updates))
        result = None
        try:
            if not self.dry_run:
                result = self.client.quotas.update(tenant_id=project_id, **updates)
        except novaclient.exceptions.NotFound as e:
            self.log_error(e)
        return result

    def update_quota_class(self, class_name='default', updates=None):
        if not updates:
            updates = {}
        return self.client.quota_classes.update(class_name, **updates)

    def get_quota_class(self, class_name='default'):
        return self.client.quota_classes.get(class_name)

    def list_users(self):
        """ Return a list of email for users that have instance(s) on a host """
        instances = self.__get_instances()
        emails = set()
        for i in instances:
            email = urllib2.unquote(i.user_id)
            # avoid system users in list
            if "@" in email:
                emails.add(email.lower())
                self.logger.debug("=> add %s to email list" % email)
            else:
                self.logger.debug("=> drop %s from email list" % email)
        return list(emails)

    def get_usage(self, project_id=None, start=None, end=None):
        if not start:
            start = datetime.today() - timedelta(days=7)
        if not end:
            end = datetime.today()
        if isinstance(start, date):
            start = datetime.combine(start, datetime.min.time())
        if isinstance(end, date):
            end = datetime.combine(end, datetime.min.time())
        if project_id:
            usage = self.client.usage.get(tenant_id=project_id, start=start, end=end)
        else:
            usage = self.client.usage.list(detailed=True, start=start, end=end)
        return usage


    def get_stats(self):
        instances = self.__get_all_instances()
        stats = dict()
        stats['count'] = len(instances)
        stats['error'] = 0
        for i in instances:
            if i.status == 'ERROR':
                stats['error'] += 1
        return stats

    def stop_instances(self, state='ACTIVE'):
        """ Stop all instances on a host with one state
        `**host`` fqdn for the nova compute host
        `**state`` stop all instances with this state
        """
        self.__change_status('stop', state)

    def start_instances(self):
        """ Start all instances on a host with state SHUTOFF
        `**host`` fqdn for the nova compute host
        """
        self.__change_status('start', 'SHUTOFF')


    def delete_instances(self, state='SHUTOFF'):
        """ Delete all instances on a host with one state
        `**host`` fqdn for the nova compute host
        `**state`` delete all instances with this state
        """
        self.__change_status('delete', state)

    def get_client(self):
        return self.client

################################### FLAVOR ####################################

    def update_flavor(self, name, spec, properties=None, public=True):
        """
        Update flavor with new spec or propertiesself.
        Note: Update require a delete and create with new ID
        Version: 2018-7
        """
        dry_run_txt = ' DRY_RUN:' if self.dry_run else ''
        flavor = self.get_by_name('flavor', name)
        if not flavor:
            # Create new flavor
            self.logger.debug('=>%s create flavor %s', dry_run_txt, name)
            if not self.dry_run:
                flavor = self.client.flavors.create(name=name,
                                                    ram=spec['ram'],
                                                    vcpus=spec['vcpus'],
                                                    disk=spec['disk'],
                                                    is_public=public)
        # Check to see if an update are needed
        update = False
        if flavor and getattr(flavor, 'os-flavor-access:is_public') != public:
            update = True
        for k, v in spec.iteritems():
            if flavor and v != getattr(flavor, k):
                update = True
        if update:
            self.logger.debug('=>%s update flavor %s', dry_run_txt, name)
            if not self.dry_run:
                # delete old
                self.client.flavors.delete(flavor.id)
                # create new
                flavor = self.client.flavors.create(name=name,
                                                    ram=spec['ram'],
                                                    vcpus=spec['vcpus'],
                                                    disk=spec['disk'],
                                                    is_public=public)
        # if no flavor we cannot do properties
        if not flavor:
            return
        # Unset old properties
        for k, v in flavor.get_keys().iteritems():
            if k not in properties:
                if not self.dry_run:
                    flavor.unset_keys([k])
                self.logger.debug('=>%s unset flavor properties %s', dry_run_txt, k)
        # Add new properties
        update = False
        if not properties:
            return
        flavor_keys = flavor.get_keys()
        for k, v in properties.iteritems():
            # flavor keys return everything as unicode so we use string match
            if str(v) != flavor_keys.get(k):
                self.logger.debug('=>%s set flavor properties %s', dry_run_txt, k)
                if not self.dry_run:
                    try:
                        flavor.set_keys({k:v})
                    except novaclient.exceptions.BadRequest as e:
                        self.logger.debug('=> %s', e)

    def get_flavors(self, class_filter=None, sort_key='memory_mb', sort_dir='asc'):
        """
            Get flavor list. Without filter all flavors will be returned
            Version: 2021-3
            :param class_filter: flavor class, e.g. m1 or vgpu.m1.
            :rtype: List of novaclient.v2.flavors.Flavor
        """
        flavors = self.client.flavors.list(detailed=True,
                                           is_public=None,
                                           sort_key=sort_key,
                                           sort_dir=sort_dir)
        flavors_filtered = list()
        for flavor in flavors:
            if not class_filter:
                flavors_filtered.append(flavor)
                continue
            flavor_class = flavor.name.rsplit('.', 1)[0]
            if class_filter == flavor_class:
                self.logger.debug('=> added %s to list' % flavor.name)
                flavors_filtered.append(flavor)
            else:
                self.logger.debug('=> %s filterd out of list' % flavor.name)
        return flavors_filtered

    def purge_flavors(self, class_filter, flavors):
        """
            Purge flavors not defined in flavor list
            Version: 2021-3
            :param class_filter: flavor class, e.g. m1 or vgpu.m1.
            :rtype: Boolean
        """
        current_flavors = self.get_flavors(class_filter=class_filter)
        purged = False
        for flavor in current_flavors:
            if flavor.name not in flavors[class_filter]:
                self.debug_log('delete flavor {}'.format(flavor.name))
                if not self.dry_run:
                    self.client.flavors.delete(flavor.id)
                purged = True
        return purged

    def delete_flavors(self, class_filter):
        """
            Delete all flavor of a class
            Version: 2021-3
            :param class_filter: flavor class, e.g. m1 or vgpu.m1.
            :rtype: Boolean
        """
        current_flavors = self.get_flavors(class_filter=class_filter)
        deleted = False
        for flavor in current_flavors:
            self.debug_log('delete flavor {}'.format(flavor.name))
            if not self.dry_run:
                self.client.flavors.delete(flavor.id)
            deleted = True
        return deleted

    def update_flavor_access(self, class_filter, project_id, action):
        """
            Grant or revoke access to flavor from project
            :param class_filter: flavor class, e.g. m1 or vgpu.m1.
            Version: 2021-3
        """
        dry_run_txt = 'DRY-RUN: ' if self.dry_run else ''
        if action == 'revoke':
            action_func = 'remove_tenant_access'
        else:
            action_func = 'add_tenant_access'
        flavors = self.get_flavors(class_filter=class_filter)
        access_updated = False
        if not flavors:
            self.debug_log('no flavors match class {}'.format(class_filter))
        for flavor in flavors:
            try:
                if not self.dry_run:
                    getattr(self.client.flavor_access, action_func)(flavor.id,
                                                                    project_id)
                self.logger.debug('=> %s%s access to %s' %
                                  (dry_run_txt, action, flavor.name))
                access_updated = True
            except novaclient.exceptions.Conflict:
                self.logger.debug('=> access exsists for %s' %
                                  (flavor.name))
            except novaclient.exceptions.NotFound:
                self.logger.debug('=> unable to %s %s' %
                                  (action, flavor.name))
        return access_updated

    def get_flavor_access(self, filters):
        flavors = self.get_flavors(filters)
        access_list = dict()
        for flavor in flavors:
            if getattr(flavor, 'os-flavor-access:is_public'):
                self.debug_log('%s is public and have no access' % flavor.name)
                continue
            access_list[flavor.name] = self.client.flavor_access.list(flavor=flavor.id)
        return access_list

################################## STATIC #####################################

    @staticmethod
    def get_compute_host(instance, short=True):
        """ This will return the name of the compte host for an instance """
        hostname = getattr(instance, 'OS-EXT-SRV-ATTR:host')
        if short:
            return hostname.split('.')[0]
        return hostname

################################## PRIVATE ####################################

    def __change_status(self, action='start', state='SHUTOFF', instances=None):
        if not instances:
            instances = self.__get_instances()
        count = 0
        for i in instances:
            if i.status == state:
                getattr(i, action)()
                count += 1
                self.instances[i.name] = i.id
                self.logger.debug('=> change status to %s on %s' % (action, i.name))
            else:
                self.logger.debug('=> %s had not status %s' % (i.name, state))
        self.logger.debug("=> Run %s on %s instances with state %s" % (action, count, state))

    def __get_instances(self, host=None):
        search_opts = dict(all_tenants=1, host=host)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances

    def __get_all_instances(self, search_opts=None, per_page=1000):
        if not search_opts:
            search_opts = dict(all_tenants=1)
        try:
            marker = None
            instances = list()
            while True:
                i = self.client.servers.list(detailed=True,
                                             search_opts=search_opts,
                                             marker=marker,
                                             limit=per_page)
                instances += i
                if len(i) >= per_page:
                    marker = i[-1].id # marker is the last element
                else:
                    break # end of loop
        except novaclient.exceptions.ClientException as e:
            self.log_error(e)
            return list()
        return instances

    def __get_aggregate(self, aggregate):
        aggregates = self.client.aggregates.list()
        for a in aggregates:
            if a.name == aggregate:
                return a
        return None
