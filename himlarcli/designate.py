from himlarcli.client import Client
from designateclient.v2 import client as designateclient


class Designate(Client):

    VERSION = 2
    SERVICE_TYPE = 'dns'

    def __init__(self, config_path, debug=False, log=None, region=None):
        """ Create a new designate client to manaage DNS
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


    # Hello world example
    def create_domain(self, name, email):
        zone = self.client.zones.create(name, email=email)
        return zone
