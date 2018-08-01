from himlarcli.client import Client
import tweepy
from himlarcli import utils

class Twitter(Client):

    def __init__(self, config_path, debug=False, log=None):
        super(Twitter, self).__init__(config_path, debug, log)
        self.logger.debug('=> config file: %s' % config_path)
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

    def get_client(self):
        return self.client
