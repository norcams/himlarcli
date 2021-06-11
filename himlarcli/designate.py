from himlarcli.client import Client
from designateclient.v2 import client as designateclient


class Designate(Client):

    VERSION = 2
    SERVICE_TYPE = 'dns'

    def __init__(self, config_path, debug=False, log=None, region=None):
        """ Create a new designate client to manage DNS
        `**config_path`` path to ini file with config
        `**log` logger object
        """
        super(Designate, self).__init__(config_path, debug, log, region)
        self.client = designateclient.Client(session=self.sess,
                                             service_type=self.SERVICE_TYPE,
                                             region_name=self.region)

    def get_client(self):
        """ Return the designate client """
        return self.client

    #-------------------------------------------------------------------
    # Blacklists functions
    #-------------------------------------------------------------------
    def list_blacklists(self):
        result = self.client.blacklists.list()
        if result:
            return result
            #return result.to_dict()
        return dict()

    def create_blacklist(self, pattern, description):
        res = self.client.blacklists.create(pattern=pattern, description=description)
        return res

    def delete_blacklist(self, blacklist_id):
        res = self.client.blacklists.delete(blacklist_id=blacklist_id)
        return res

    def update_blacklist(self, blacklist_id, values):
        res = self.client.blacklists.update(blacklist_id=blacklist_id, values=values)
        return res

    def get_blacklist(self, blacklist_id):
        res = self.client.blacklists.get(blacklist_id=blacklist_id)
        return res

    #-------------------------------------------------------------------
    # TLDs functions
    #-------------------------------------------------------------------
    def list_tlds(self):
        result = self.client.tlds.list(limit=9999)
        if result:
            return result
            #return result.to_dict()
        return dict()

    def create_tld(self, name, description):
        res = self.client.tlds.create(name=name, description=description)
        return res

    def delete_tld(self, tld):
        res = self.client.tlds.delete(tld=tld)
        return res

    def update_tld(self, tld, values):
        res = self.client.tlds.update(tld=tld, values=values)
        return res

    def get_tld(self, name):
        res = self.client.tlds.get(tld=name)
        return res

    #-------------------------------------------------------------------
    # Zone functions
    #-------------------------------------------------------------------
    def list_all_zones(self):
        self.client.session.all_projects = 1
        res = self.client.zones.list()
        return res

    def list_project_zones(self, project_id):
        self.client.session.sudo_project_id = project_id
        res = self.client.zones.list()
        self.client.session.sudo_project_id = None
        return res

    def delete_project_zone(self, zone_id, project_id):
        self.client.session.sudo_project_id = project_id
        res = self.client.zones.delete(zone_id)
        self.client.session.sudo_project_id = None
        return res
