import ConfigParser
import sys
import requests
import json
from himlarcli import utils

class Slack(object):

    def __init__(self, config_path, debug=False, log=None):
        debug_level = 1 if debug else 0
        self.config_path = config_path
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
        self.debug = debug
        self.dry_run = False
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
            self.logger.debug('=> %s', log_msg)
        else:
            log_msg = 'DRY-RUN: ' + log_msg


    def set_dry_run(self, dry_run):
        self.dry_run = dry_run

    def get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s'
                              % (section, option))
        except ConfigParser.NoSectionError:
            self.logger.debug('=> config file missing section %s' % section)
        return None

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write("%s\n" % msg)
        if code > 0:
            sys.exit(code)
