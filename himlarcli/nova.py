from client import Client
from novaclient import client as novaclient
from novaclient.exceptions import NotFound
import urllib2
import json

class Nova(Client):
    version = 2
    instances = dict()

    def __init__(self, config_path, host=None, debug=False):
        """ Create a new nova client to manaage a host
        `**host`` fqdn for the nova compute host
        `**config_path`` path to ini file with config
        """
        super(Nova,self).__init__(config_path, debug)
        self.client = novaclient.Client(self.version, session=self.sess)
        self.host = host

    def valid_host(self):
        try:
            self.client.hosts.get(self.host)
            valid = True
        except NotFound as e:
            valid = False
        return valid

    def set_host(self, host):
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
            self.log("list_instances(): instance %s for %s" % (i.name, email))
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
                self.log("list_users(): add %s to email list" % email)
            else:
                self.log("list_users(): drop %s from email list" % email)
        return list(emails)

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
        self.__save_instances()

    def start_instances(self):
        """ Start all instances on a host with state SHUTOFF
        `**host`` fqdn for the nova compute host
        """
        self.__change_status('start', 'SHUTOFF')
        #self.__save_instances()

    def start_instances_from_file(self):
        """ Start all instances on a host from a maintenance file
        `**host`` fqdn for the nova compute host
        """
        self.__load_instances()
        count = 0
        for name, id in self.instances.iteritems():
            i = self.client.servers.get(id)
            i.start()
            count += 1
            self.log("Starting %s" % name)
        print "run start on %s instances with state SHUTOFF" % (count)

    def delete_instances(self, state='SHUTOFF'):
        """ Delete all instances on a host with one state
        `**host`` fqdn for the nova compute host
        `**state`` delete all instances with this state
        """
        self.__change_status('delete', state)
        #self.__save_instances()

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
                self.log('Change status to %s on %s' % (action, i.name))
            else:
                print i.id
                self.log('%s had not status %s' % (i.name, state))

        print "run %s on %s instances with state %s" % (action, count, state)

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

    def __save_instances(self):
        if bool(self.instances) == False:
            return
        try:
            maintenance = self.config._sections['maintenance']
        except KeyError as e:
            self.logger.exception('missing [maintenance]')
        if maintenance['instance_file']:
            file = maintenance['instance_file']
            with open(file, 'w') as f:
                self.log("save instances to %s" % file)
                json.dump(self.instances, f)

    def __load_instances(self):
        try:
            maintenance = self.config._sections['maintenance']
        except KeyError as e:
            self.logger.exception('missing [maintenance]')
        if maintenance['instance_file']:
            file = maintenance['instance_file']
            with open(file, 'r') as f:
                self.instances = json.load(f)
                self.log("read instances from %s" % file)
