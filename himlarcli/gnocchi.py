from himlarcli.client import Client
from gnocchiclient.v1.client import Client as gnocchiclient

class Gnocchi(Client):

    def __init__(self, config_path, debug=False, log=None, region=None):
        super(Gnocchi, self).__init__(config_path, debug, log, region)
        self.logger.debug('=> init gnocchi client for region %s' % self.region)
        adapter_options = {'region_name': self.region}
        self.client = gnocchiclient(session=self.sess,
                                    adapter_options=adapter_options)


    def get_client(self):
        return self.client
