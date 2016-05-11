from client import Client
from novaclient import client as novaclient
import urllib2

class Nova(Client):
    version = 2

    def __init__(self, config_path):
        super(Nova,self).__init__(config_path)
        self.client = novaclient.Client(self.version, session=self.sess)

    def get(self):
        return self.client

    def list_users(self, host):
        instances = self.__get_instances(host)
        list = []
        for i in instances:
            list.append(urllib2.unquote(i._info['user_id']))
        return list

    def stop_instances(self, host):
        self.__change_status(host, 'stop', 'ACTIVE')

    def start_instances(self, host):
        self.__change_status(host)

    def delete_instances(self, host, state='SHUTOFF'):
        self.__change_status(host, 'delete', state)

    def __change_status(self, host, action='start', state='SHUTOFF'):
        instances = self.__get_instances(host)
        count = 0
        for i in instances:
            if i._info['status'] == state:
                getattr(i, action)()
                count += 1
        print "run %s on %s instances with state %s" % (action, count, state)

    def __get_instances(self, host):
        search_opts = dict(all_tenants=1, host=host)
        instances = self.client.servers.list(detailed=True,
                                             search_opts=search_opts)
        return instances
