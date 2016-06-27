from client import Client
from novaclient import client as novaclient
from novaclient.exceptions import NotFound
import urllib2
import json

class Nova(Client):
    version = 2
    instances = dict()

    def __init__(self, config_path, host=None, debug=False, log=None):
        """ Create a new nova client to manaage a host
        `**host`` fqdn for the nova compute host
        `**config_path`` path to ini file with config
        """
        super(Nova,self).__init__(config_path, debug, log)
        self.client = novaclient.Client(self.version, session=self.sess)
        self.set_host(host)

    def valid_host(self):
        try:
            self.client.hosts.get(self.host)
            valid = True
        except NotFound as e:
            valid = False
        return valid

    def set_host(self, host):
        if not host:
            self.host = None
            return
        domain = self.config.get('openstack', 'domain')
        if domain and not '.' in host:
            self.logger.debug("=> prepend %s to %s" % (domain, host))
            host = host + '.' + domain
        self.host = host

    def list_instances(self):
        instances = self.__get_instances()
        users = dict()
        for i in instances:
            email = urllib2.unquote(i._info['user_id'])
            if email not in users.keys():
                users[email] = {}
            if len(i._info['addresses']['public']) > 0:
                ip = i._info['addresses']['public'][0]['addr']
            else:
                ip = '<no public ip>'
            name = i._info['name']
            users[email][name] = { 'ip': ip, 'status': i._info['status']}
            self.logger.debug("=> instance %s for %s" % (i.name, email))
        return users

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

    #
    # private methods
    #
    def __change_status(self, action='start', state='SHUTOFF'):
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

    def __get_instances(self):
        if not self.valid_host():
            return list()
        search_opts = dict(all_tenants=1, host=self.host)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances

    def __get_all_instances(self):
        search_opts = dict(all_tenants=1)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances
