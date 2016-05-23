from client import Client
from keystoneclient.v3 import client as keystoneclient

class Keystone(Client):
    version = 3

    def __init__(self, config_path, debug=False):
        super(Keystone,self).__init__(config_path, debug)
        self.client = keystoneclient.Client(session=self.sess)

    def get_domain_id(self, domain):
        return self.__get_domain(domain)

    def get_client(self):
        return self.client

    def get_region(self):
        return self.config._sections['openstack']['region']

    def get_project_count(self, domain=False):
        projects = self.__get_projects(domain)
        return len(projects)

    def list_projects(self, domain=False):
        project_list = self.__get_projects(domain)
        projects = list()
        for i in project_list:
            projects.append(i.name)
        return projects

    def __get_domain(self, domain):
        domain = self.client.domains.list(name=domain)
        if len(domain) > 0:
            return domain[0].id
        else:
            return False

    def __get_projects(self, domain=False):
        if domain:
            domain_id = self.__get_domain(domain)
            projects = self.client.projects.list(domain=domain_id)
        else:
            projects = self.client.projects.list()
        return projects
