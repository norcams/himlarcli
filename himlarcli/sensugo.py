from himlarcli.client import Client
import sensu_go
import inspect
from himlarcli import utils

class SensuGo(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(SensuGo, self).__init__(config_path, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        api_url = self.get_config('sensugo', 'url')
        self.client = sensu_go.Client(address=self.get_config('sensugo', 'url'),
                                      username=self.get_config('sensugo', 'username'),
                                      password=self.get_config('sensugo', 'password'),
                                      #verify=False,
                                      ca_path=self.get_config('sensugo', 'ca_path'))

    def get_client(self):
        return self.client

    def get_events(self):
        events = self.client.events.list()
        return events

    def get_silenced(self, host, check):
        return self.client.silences.get(f'entity:{host}:{check}')

    def list_silenced(self):
        hosts = self.client.silences.list()
        return hosts

    def clear_silenced(self, host, check):
        self.client.silences.delete(f'entity:{host}:{check}')

    def silence_check(self, host, check, expire='-1', reason='himlarcli'):
        spec = {
            'subscription': f'entity:{host}',
            'check': check,
            'expire': int(expire),
            'expire_on_resolve': True,
            'reason': reason}
        metadata = { 'name': f'entity:{host}:{check}' }
        self.client.silences.create(spec=spec, metadata=metadata)

    def delete_client(self, host):
        pass

    # TODO
    # def delete_client(self, host):
    #     url = self.api_url
    #     endpoint = '/clients/' + host
    #     if not self.dry_run:
    #         try:
    #             response = self.session.delete(url+endpoint, timeout=5)
    #             self.logger.debug('=> %s' % response.status_code)
    #         except requests.exceptions.ConnectionError:
    #             pass
    #     else:
    #         self.logger.debug('=> DRY-RUN: deleted %s' % host)
    #
    #
