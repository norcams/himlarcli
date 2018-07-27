import ConfigParser
import sys
import tweepy
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
        self.key = self.get_config('twitter', 'api_key')
        self.secret_key = self.get_config('twitter', 'api_secret_key')
        self.access_token = self.get_config('twitter', 'access_token')
        self.access_secret_token = self.get_config('twitter', 'access_secret_token')

    def auth(self):
        auth = tweepy.OAuthHandler(self.key, self.secret_key)
        auth.set_access_token(self.access_token, self.access_secret_token)
        return auth

    def publish_twitter(self, msg):
        auth = self.auth()
        api = tweepy.API(auth)
        log_msg = 'Message published to Twitter: %s' % msg
        if not self.dry_run:
            api.update_status(msg)
        else:
            log_msg = 'DRY-RUN: ' + log_msg
        self.logger.debug('=> %s', log_msg)

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
