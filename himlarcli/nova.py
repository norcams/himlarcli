from client import Client
from novaclient import client as novaclient
from novaclient.exceptions import NotFound
import urllib2

class Nova(Client):
    version = 2

    def __init__(self, config_path, host):
        """ Create a new nova client to manaage a host
        `**host`` fqdn for the nova compute host
        `**config_path`` path to ini file with config
        """
        super(Nova,self).__init__(config_path)
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

    def list_users(self):
        """ Return a list of email for users that have instance(s) on a host """
        instances = self.__get_instances()
        emails = set()
        for i in instances:
            emails.add(urllib2.unquote(i._info['user_id']).lower())
        return list(emails)

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
        print "run %s on %s instances with state %s" % (action, count, state)

    def __get_instances(self):
        if not self.valid_host():
            return list()
        search_opts = dict(all_tenants=1, host=self.host)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances
