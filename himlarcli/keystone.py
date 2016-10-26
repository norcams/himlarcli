from client import Client
from keystoneclient.v3 import client as keystoneclient

class Keystone(Client):
    version = 3

    def __init__(self, config_path, debug=False):
        super(Keystone,self).__init__(config_path, debug)
        self.client = keystoneclient.Client(session=self.sess,
                                            region_name=self.region)

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

    """ Federation settings for identity provider """
    def set_identity_provider(self, name, remote_id):
        providers = self.client.federation.identity_providers.list()
        for i in providers:
            if name == i.id:
                self.logger.debug('=> identity provider %s exists' % name)
                return
        self.client.federation.identity_providers.create(id=name,
                                                         enabled=True,
                                                         remote_ids=[remote_id])

    """ Federation settings for identity mappping """
    def set_mapping(self, id, rules):
        mappings = self.client.federation.mappings.list()
        for i in mappings:
            if id == i.id:
                self.logger.debug('=> mapping %s exists' % id)
                return
        self.client.federation.mappings.create(mapping_id=id, rules=rules)

    """ Federation settings for protocol container """
    def set_protocol(self, id, provider, mapping):
        protocols = self.client.federation.protocols.list(provider)
        for i in protocols:
            if id == i.id:
                self.logger.debug('=> protocol %s exists' % id)
                return
        self.client.federation.protocols.create(id,
                                                identity_provider=provider,
                                                mapping=mapping)

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
