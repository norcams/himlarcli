from himlarcli.client import Client
import sensu_go
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
    # def silence_host(self, host, expire=None, reason=None):
    #     url = self.api_url
    #     endpoint = '/silenced'
    #     payload = {'subscription': 'client:' + host,
    #                'creator': 'himlarcli',
    #                'reason': 'Silenced by himlarcli'}
    #
    #     # Update payload with options
    #     if expire:
    #         payload.update({'expire': int(expire)})
    #     else:
    #         payload.update({'expire_on_resolve': True})
    #     if reason:
    #         payload.update({'reason': reason})
    #
    #     json_payload = json.dumps(payload)
    #     try:
    #         response = self.session.post(url+endpoint,
    #                                      headers=self.headers,
    #                                      data=json_payload,
    #                                      timeout=5)
    #         self.logger.debug('=> HTTP Status: %s' % (response.status_code))
    #     except requests.exceptions.ConnectionError:
    #         pass
    #
    # def list_silenced(self):
    #     url = self.api_url
    #     endpoint = '/silenced'
    #     reponse = self.session.get(url+endpoint, headers=self.headers)
    #     print(reponse.text)
    #
    # def clear_silenced(self, host):
    #     url = self.api_url
    #     endpoint = '/silenced/clear'
    #     payload = {'subscription': 'client:' + host}
    #     json_payload = json.dumps(payload)
    #     response = self.session.post(url+endpoint,
    #                                  headers=self.headers,
    #                                  data=json_payload)
    #     self.logger.debug('=> %s' % response.status_code)
