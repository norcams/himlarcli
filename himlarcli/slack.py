from himlarcli.client import Client
import requests
import json
from himlarcli import utils

class Slack(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(Slack, self).__init__(config_path, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.webhook_url = self.get_config('slack', 'url')
        self.slack_user = self.get_config('slack', 'user')
        self.slack_channel = self.get_config('slack', 'channel')

    def publish_slack(self, msg):
        url = self.webhook_url
        payload = {"channel": self.slack_channel,
                   "username": self.slack_user,
                   "text": msg}
        json_payload = json.dumps(payload)
        log_msg = 'Message published to %s by %s: %s' % (self.slack_channel, self.slack_user, msg)
        if not self.dry_run:
            requests.post(url, data=json_payload)
        else:
            log_msg = 'DRY-RUN: ' + log_msg
        self.logger.debug('=> %s', log_msg)

    def get_client(self):
        return self.client
