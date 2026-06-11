import configparser
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from himlarcli import utils

class Slack:

    def __init__(self, config_path, debug=False, log=None):
        self.config_path = config_path
        self.config = utils.get_himlarcli_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.dry_run = False
        token = self.get_config('slack_publish', 'token')
        self.default_channel = self.get_config('slack_publish', 'channel')
        self.client = WebClient(token=token)

    def set_dry_run(self, dry_run):
        self.dry_run = True if dry_run else False

    def publish_slack(self, msg, channel=None):
        if not channel:
            channel = self.default_channel
        log_msg = 'Message published to %s: %s' % (channel, msg)
        if not self.dry_run:
            try:
                self.client.chat_postMessage(channel=channel, text=msg)
            except SlackApiError as e:
                self.logger.error('=> Slack post failed: %s', e.response['error'])
                return
        else:
            log_msg = 'DRY-RUN: ' + log_msg
        self.logger.debug('=> %s', log_msg)

    def get_config(self, section, option):
        try:
            return self.config.get(section, option)
        except (configparser.NoOptionError, configparser.NoSectionError):
            return None
