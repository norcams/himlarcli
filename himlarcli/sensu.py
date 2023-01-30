from himlarcli.client import Client
import requests
import json
from himlarcli import utils

class Sensu(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(Sensu, self).__init__(config_path, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.api_url = self.get_config('sensu', 'url')
        self.session = requests.Session()
        self.session.auth = (self.get_config('sensu', 'username'),
                             self.get_config('sensu', 'password'))
        self.headers = {'Content-Type': 'application/json'}

    # More functions will be added when we need them.

    def delete_client(self, host):
        url = self.api_url
        endpoint = '/clients/' + host
        if not self.dry_run:
            try:
                response = self.session.delete(url+endpoint)
                self.logger.debug('=> %s' % response.status_code)
            except requests.exceptions.ConnectionError:
                pass
        else:
            self.logger.debug('=> DRY-RUN: deleted %s' % host)


    def silence_host(self, host, expire=None):
        url = self.api_url
        endpoint = '/silenced'
        payload = {'subscription': 'client:' + host,
                   'creator': 'himlarcli',
                   'reason': 'Silenced by himlarcli'}
        if expire:
            payload.update({'expire': int(expire)})
        else:
            payload.update({'expire_on_resolve': True})
        json_payload = json.dumps(payload)
        response = self.session.post(url+endpoint,
                                     headers=self.headers,
                                     data=json_payload)
        self.logger.debug('=> HTTP Status: %s' % (response.status_code))

    def list_silenced(self):
        url = self.api_url
        endpoint = '/silenced'
        reponse = self.session.get(url+endpoint, headers=self.headers)
        print(reponse.text)

    def clear_silenced(self, host):
        url = self.api_url
        endpoint = '/silenced/clear'
        payload = {'subscription': 'client:' + host}
        json_payload = json.dumps(payload)
        response = self.session.post(url+endpoint,
                                     headers=self.headers,
                                     data=json_payload)
        self.logger.debug('=> %s' % response.status_code)

    def get_client(self):
        return self.client
