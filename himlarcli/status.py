from himlarcli.client import Client
import requests
import json
from himlarcli import utils

class Status(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(Status, self).__init__(config_path, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.api_url = self.get_config('status', 'url')
        self.auth_token = ('Bearer %s' % self.get_config('status', 'token'))

    def publish_status(self, msg, msg_type='info'):
        url = self.api_url
        headers = {'Content-Type': 'application/json',
                   'Accept': 'application/problem+json',
                   'Authorization': self.auth_token}
        payload = {"message": msg,
                   "message_type": msg_type}
        json_payload = json.dumps(payload)
        log_msg = 'Message published to status marked %s: %s' % (msg_type, msg)
        if not self.dry_run:
            response = requests.post(url, headers=headers, data=json_payload)
            self.logger.debug('=> %s, Status: %s' % (log_msg, response.status_code))
        else:
            self.logger.debug('DRY-RUN: %s' % msg)

    def list_status(self):
        url = self.api_url
        headers = {'Content-Type': 'application/json'}
        reponse = requests.get(url, headers=headers)
        print(reponse.text)

    def delete_status(self, status_id):
        url = ('%s/%s' % (self.api_url, status_id))
        headers = {'Accept': 'application/problem+json',
                  'Authorization': self.auth_token}
        if not self.dry_run:
            response = requests.delete(url, headers=headers)
            self.logger.debug('=> %s' % response.status_code)
        else:
            self.logger.debug('DRY-RUN: Deleting %s' % url)

    def get_client(self):
        return self.client
