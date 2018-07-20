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
        bl = self.client.blacklists.create(pattern=pattern, description=description)
        return bl

    def delete_blacklist(self, blacklist_id):
        bl = self.client.blacklists.delete(blacklist_id=blacklist_id)
        return bl

    def update_blacklist(self, blacklist_id, values):
        bl = self.client.blacklists.update(blacklist_id=blacklist_id, values=values)
        return bl

    #-------------------------------------------------------------------
    # Zones functions
    #-------------------------------------------------------------------
    def list_zones(self):
        result = self.client.zones.list()
        if result:
            return result
            #return result.to_dict()
        return dict()

    #-------------------------------------------------------------------
    # TLDs functions
    #-------------------------------------------------------------------
    def list_tlds(self):
        result = self.client.tlds.list()
        if result:
            return result
            #return result.to_dict()
        return dict()

    def create_tld(self, name, description):
        tld = self.client.tlds.create(name, description)
        return tld
