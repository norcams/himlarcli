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

    def publish_slack(self, msg, channel=None, user=None):
        if not channel:
            channel = self.slack_channel
        if not user:
            user = self.slack_user
        url = self.webhook_url
        payload = {"channel": channel,
                   "username": user,
                   "text": msg}
        json_payload = json.dumps(payload)
        log_msg = 'Message published to %s by %s: %s' % (channel, user, msg)
        if not self.dry_run:
            requests.post(url, data=json_payload)
        else:
            log_msg = 'DRY-RUN: ' + log_msg
        self.logger.debug('=> %s', log_msg)

    def get_client(self):
        return self.client
