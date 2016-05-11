from client import Client
from keystoneclient.v3 import client as keystoneclient

class Keystone(Client):
    version = 3

    def __init__(self, config_path):
        super(Keystone,self).__init__(config_path)
        self.client = keystoneclient.Client(session=self.sess)

    def get_client(self):
        return self.client

    def list_projects(self, domain=False):
        if domain:
            domain_id = self.__get_domain(domain)
            projects = self.client.projects.list(domain=domain_id)
        else:
            projects = self.client.projects.list()
        list = []
        for i in projects:
            list.append(i.name)
        return list

    def __get_domain(self, domain):
        domain = self.client.domains.list(name=domain)
        if len(domain) > 0:
            return domain[0].id
        else:
            return False
