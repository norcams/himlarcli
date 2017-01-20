from client import Client
from novaclient import client as novaclient
from keystoneclient.v3 import client as keystoneclient
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
        super(Nova,self).__init__(config_path, debug, log, region)
        self.client = novaclient.Client(self.version,
                                        session=self.sess,
                                        region_name=self.region)

    """ Create a new keystone client if needed and then return the client """
    def get_keystone_client(self):
        if not self.ksclient:
            self.ksclient = keystoneclient.Client(session=self.sess,
                                                  region_name=self.region)
        return self.ksclient

################################## AGGREGATE ##################################

    def get_aggregate(self, aggregate):
        aggregate = self.__get_aggregate(aggregate)
        return aggregate

    def update_aggregate(self, aggregate, metadata):
        aggregate = self.__get_aggregate(aggregate)
        return self.client.aggregates.set_metadata(aggregate.id, metadata)

    def get_instances(self, aggregate=None, simple=False):
        if not aggregate:
            instances = self.__get_instances()
        else:
            agg = self.__get_aggregate(aggregate)
            if not agg.hosts:
                self.logger.debug('=> not hosts found in aggregate %s' % aggregate)
                instances = list()
            else:
                for h in agg.hosts:
                    self.logger.debug('=> hosts %s found in aggregate %s' % (h, aggregate))
                    instances = self.__get_instances(h)
        self.logger.debug("=> found %s instances in %s" % (len(instances), aggregate))
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
            user = self.ksclient.users.get(i.user_id)
            self.logger.debug('=> found user %s for instance %s' % (user.name, i.name))
            if not simple:
                emails.append(user)
            elif "@" in user.name:
                emails.add(user.name.lower())
                self.logger.debug("=> add %s to user list" % user.name)
        return emails

    def delete_project_instances(self, project_id):
        search_opts = dict(tenant_id=project_id, all_tenants=1)
        instances = self.__get_all_instances(search_opts=search_opts)
        self.__change_status(action='stop', state='ACTIVE', instances=instances)
        if len(instances) > 0:
            time.sleep(60)
        self.__change_status(action='delete', state='SHUTOFF', instances=instances)

    def list_quota(self, project_id):
        return self.client.quotas.get(tenant_id=project_id)

    def set_quota(self, project_id, quota):
        self.logger.debug('=> quota set to %s' % quota)
        self.client.quotas.update(project_id, **quota)

    def list_users(self):
        """ Return a list of email for users that have instance(s) on a host """
        instances = self.__get_instances()
        emails = set()
        for i in instances:
            email = urllib2.unquote(i._info['user_id'])
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

    def get_stats(self, domain=None):
        instances = self.__get_all_instances()
        stats = dict()
        stats['count'] = len(instances)
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
            if instance._info['status'] != 'ACTIVE':
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

    """ Update is not an option. We delete and create a new flavor! """
    def update_flavor(self, name, spec, dry_run=False):
        flavors = self.get_flavors()
        found = False
        for f in flavors:
            if f._info['name'] != name:
                continue
            found = True
            update = False
            for k,v in spec.iteritems():
                if v != f._info[k]:
                    update = True
            if update and not dry_run:
                self.logger.debug('=> updated flavor %s' % name)
                # delete old
                self.client.flavors.delete(f._info['id'])
                # create new
                self.client.flavors.create(name=name,
                                            ram=spec['ram'],
                                            vcpus=spec['vcpus'],
                                            disk=spec['disk'])
            elif update and dry_run:
                self.logger.debug('=> dry-run: update %s: %s' % (name,spec))
            else:
                self.logger.debug('=> no update needed for %s' % name)
        if not found:
            self.logger.debug('=> create new flavor %s: %s' % (name, spec))
            if not dry_run:
                self.client.flavors.create(name=name,
                                           ram=spec['ram'],
                                           vcpus=spec['vcpus'],
                                           disk=spec['disk'])

    def get_flavors(self):
        flavors = self.client.flavors.list(detailed=True, is_public=True)
        return flavors

################################## PRIVATE ####################################

    def __change_status(self, action='start', state='SHUTOFF', instances=None):
        if not instances:
            instances = self.__get_instances()
        count = 0
        for i in instances:
            if i._info['status'] == state:
                getattr(i, action)()
                count += 1
                self.instances[i.name] = i.id
                self.logger.debug('=> change status to %s on %s' % (action, i.name))
            else:
                print i.id
                self.logger.debug('=> %s had not status %s' % (i.name, state))

        print "Run %s on %s instances with state %s" % (action, count, state)

    def __get_instances(self, host=None):
        search_opts = dict(all_tenants=1, host=host)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances

    def __get_all_instances(self, search_opts=dict(all_tenants=1)):
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances

    def __get_aggregate(self, aggregate):
        aggregates = self.client.aggregates.list()
        for a in aggregates:
            if a.name == aggregate:
                return a
        return None
