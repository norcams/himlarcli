from client import Client
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient
import keystoneauth1.exceptions as keyexc
from novaclient.exceptions import NotFound
from datetime import datetime, date
import urllib2
import json
import pprint
import time


class Nova(Client):
    version = 2
    instances = dict()
    ksclient = None

    def __init__(self, config_path, host=None, debug=False, log=None, region=None):
        """ Create a new nova client to manaage a host
        `**host`` fqdn for the nova compute host
        `**config_path`` path to ini file with config
        """
        super(Nova, self).__init__(config_path, debug, log, region)
        self.client = novaclient.Client(self.version,
                                        session=self.sess,
                                        region_name=self.region)

    def get_keystone_client(self):
        """ Create a new keystone client if needed and then return the client """
        if not self.ksclient:
            self.ksclient = keystoneclient.Client(session=self.sess,
                                                  region_name=self.region)
        return self.ksclient
# =============================== SERVER ======================================

    def create_server(self, name, flavor, image_id, **kwargs):
        """ Create a server. Server will be crated by the user and project
            used in config.ini (default admin and openstack) """
        server = self.client.servers.create(name=name,
                                            flavor=flavor,
                                            image=image_id,
                                            **kwargs)
        return server

# =============================== HOSTS =======================================
    def get_hosts(self, zone=None):
        return self.client.hosts.list(zone=zone)

    def get_service(self, host, service='nova-compute'):
        return self.client.services.list(host=host, binary=service)

    def enable_host(self, name, service='nova-compute'):
        self.logger.debug('=> enable host %s' % name)
        self.client.services.enable(host=name, binary=service)

    def disable_host(self, name, service='nova-compute'):
        self.logger.debug('=> disable host %s' % name)
        self.client.services.disable(host=name, binary=service)

################################## AGGREGATE ##################################

    def get_aggregates(self, simple=True):
        aggregates = self.client.aggregates.list()
        if not simple:
            return aggregates
        agg_list = list()
        for aggregate in aggregates:
            agg_list.append(aggregate.name)
        return agg_list

    def get_aggregate(self, aggregate):
        aggregate = self.__get_aggregate(aggregate)
        return aggregate

    def update_aggregate(self, aggregate, metadata):
        aggregate = self.__get_aggregate(aggregate)
        return self.client.aggregates.set_metadata(aggregate.id, metadata)

    def get_instances(self, aggregate=None, host=None, simple=False):
        if not aggregate:
            instances = self.__get_instances()
        else:
            agg = self.__get_aggregate(aggregate)
            if not agg.hosts:
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
        host_txt = ' (host=%s)' % host if host else None
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

# ============================== INSTANCES ====================================

    def get_instance(self, server_id):
        return self.client.servers.get(server=server_id)

    def get_all_instances(self, search_opts=None):
        if not search_opts:
            search_opts = {'all_tenants': 1}
        elif 'all_tenants' not in search_opts:
            search_opts.update({'all_tenants': 1})
        return self.__get_all_instances(search_opts)

    def get_project_instances(self, project_id):
        search_opts = dict(tenant_id=project_id, all_tenants=1)
        instances = self.__get_all_instances(search_opts=search_opts)
        self.logger.debug('=> found %s instances for project %s' % (len(instances), project_id))
        return instances

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

    def list_quota(self, project_id, detail=False):
        """ List a projects nova quota.

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
            start = datetime(2016, 11, 10)
        if not end:
            end = datetime.today()
        if project_id:
            usage = self.client.usage.get(tenant_id=project_id, start=start, end=end)
        else:
            usage = self.client.usage.list(detailed=True, start=start, end=end)
        return usage


    def save_states(self):
        instances = self.__get_all_instances()
        if instances:
            self.state.add_active(instances)
            self.state.close()

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


    def start_instances_from_state(self):
        """ Start all instances from a previous saved state """
        instances = self.state.get_instances(state='ACTIVE', host=self.host)
        count = 0
        for i in instances:
            instance = self.client.servers.get(i[0])
            if instance.status != 'ACTIVE':
                instance.start()
                count += 1
                self.logger.debug("=> starting %s" % i[1])
            else:
                self.logger.debug("=> already running %s" % i[1])
        print "Run start on %s instances with previous state ACTIVE" % (count)

    def delete_instances(self, state='SHUTOFF'):
        """ Delete all instances on a host with one state
        `**host`` fqdn for the nova compute host
        `**state`` delete all instances with this state
        """
        self.__change_status('delete', state)

    def get_client(self):
        return self.client

################################### FLAVOR ####################################

    def update_flavor(self, name, spec, public=True, dry_run=False):
        """ Update is not an option. We delete and create a new flavor! """
        flavors = self.get_flavors()
        found = False
        for f in flavors:
            if f.name != name:
                continue
            found = True
            update = False
            if f._info['os-flavor-access:is_public'] != public:
                update = True
            for k, v in spec.iteritems():
                if v != f._info[k]:
                    update = True
            if update and not dry_run:
                self.logger.debug('=> updated flavor %s' % name)
                # delete old
                self.client.flavors.delete(f.id)
                # create new
                self.client.flavors.create(name=name,
                                           ram=spec['ram'],
                                           vcpus=spec['vcpus'],
                                           disk=spec['disk'],
                                           is_public=public)
            elif update and dry_run:
                self.logger.debug('=> dry-run: update %s: %s' % (name, spec))
            else:
                self.logger.debug('=> no update needed for %s' % name)
        if not found:
            self.logger.debug('=> create new flavor %s: %s' % (name, spec))
            if not dry_run:
                self.client.flavors.create(name=name,
                                           ram=spec['ram'],
                                           vcpus=spec['vcpus'],
                                           disk=spec['disk'],
                                           is_public=public)


    def get_flavors(self, filters=None):
        # Setting sort_key=id and sort_dir='desc' seem to sort by flavor size!
        # DO NOT TRUST THIS SORTING
        flavors = self.client.flavors.list(detailed=True,
                                           is_public=None,
                                           sort_key='id',
                                           sort_dir='desc')
        flavors_filtered = list()
        if filters:
            for flavor in flavors:
                if filters in flavor.name:
                    self.logger.debug('=> added %s to list' % flavor.name)
                    flavors_filtered.append(flavor)
                else:
                    self.logger.debug('=> %s filterd out of list' % flavor.name)
            return flavors_filtered
        else:
            return flavors

    def purge_flavors(self, filters, flavors, dry_run=False):
        dry_run_txt = 'DRY-RUN: ' if dry_run else ''
        current_flavors = self.get_flavors(filters)
        for flavor in current_flavors:
            if flavor.name not in flavors[filters]:
                if not dry_run:
                    self.client.flavors.delete(flavor.id)
                self.logger.debug('=> %sdelete flavor %s' %
                                  (dry_run_txt, flavor.name))

    def update_flavor_access(self, filters, project_id, action, dry_run=False):
        dry_run_txt = 'DRY-RUN: ' if dry_run else ''
        if action == 'revoke':
            action_func = 'remove_tenant_access'
        else:
            action_func = 'add_tenant_access'
        flavors = self.get_flavors(filters)
        for flavor in flavors:
            try:
                if not dry_run:
                    getattr(self.client.flavor_access, action_func)(flavor.id,
                                                                    project_id)
                self.logger.debug('=> %s%s access to %s' %
                                  (dry_run_txt, action, flavor.name))

            except novaclient.exceptions.Conflict:
                self.logger.debug('=> access exsists for %s' %
                                  (flavor.name))
            except novaclient.exceptions.NotFound:
                self.logger.debug('=> unable to %s %s' %
                                  (action, flavor.name))

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

    def __get_all_instances(self, search_opts=None):
        if not search_opts:
            search_opts = dict(all_tenants=1)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances

    def __get_aggregate(self, aggregate):
        aggregates = self.client.aggregates.list()
        for a in aggregates:
            if a.name == aggregate:
                return a
        return None
