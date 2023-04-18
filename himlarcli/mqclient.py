import os
import sys
import json
import configparser
import pika
from himlarcli import utils

class MQclient():

    """Class representing a MQ client"""

    def __init__(self, config_path, debug, log=None):
        self.config = self.load_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s', self.config_path)
        self.dry_run = False
        self.debug = debug
        credentials = pika.PlainCredentials(
            username=self.__get_config('rabbitmq', 'username'),
            password=self.__get_config('rabbitmq', 'password'))

        parameters = pika.ConnectionParameters(
            host=self.__get_config('rabbitmq', 'host'),
            virtual_host=self.__get_config('rabbitmq', 'vhost'),
            credentials=credentials,
            connection_attempts=5,
            retry_delay=30,
            socket_timeout=10,
            blocked_connection_timeout=20,
            heartbeat=10)
        self.connection = pika.BlockingConnection(parameters)

    def set_dry_run(self, dry_run):
        self.logger.debug('=> set dry_run to %s in %s', dry_run, type(self).__name__)
        self.dry_run = bool(dry_run)

    def load_config(self, config_path):
        """ The config file will be loaded from the path given with the -c
            option path when running the script. If no -c option given it will
            also look for config.ini in:
                - local himlarcli root
                - /etc/himlarcli/
            If no config is found it will exit.
        """
        if config_path and not os.path.isfile(config_path):
            self.log_error(f"Could not find config file: {config_path}", 1)
        elif not config_path:
            self.config_path = None
            local_config = utils.get_abs_path('config.ini')
            etc_config = '/etc/himlarcli/config.ini'
            if os.path.isfile(local_config):
                self.config_path = local_config
            else:
                if os.path.isfile(etc_config):
                    self.config_path = etc_config
            if not self.config_path:
                msg = "Config file not found in default locations:\n  {}\n  {}"
                self.log_error(msg.format(local_config, etc_config), 1)
        else:
            self.config_path = config_path
        return utils.get_config(self.config_path)

    def get_channel(self, queue):
        channel = self.connection.channel()
        channel.queue_declare(queue=queue, durable=True)
        return channel

    def close_connection(self):
        self.connection.close()

    def push(self, email, password, action='create-project', queue='access'):
        """ Example function to push message to the message queue """
        channel = self.connection.channel()
        channel.queue_declare(queue=queue, durable=True)
        data = {
            'action': action,
            'email': email,
            'password': password
        }
        message = json.dumps(data)
        if not self.dry_run:
            channel.basic_publish(exchange='',
                                  routing_key=queue,
                                  body=message,
                                  properties=pika.BasicProperties(delivery_mode=2))
            self.logger.debug('=> message %s added to queue %s', message, queue)
        else:
            self.logger.debug('=> DRY-RUN: message %s added to queue %s', message, queue)
        self.close_connection()

    @staticmethod
    def log_error(msg, code=0):
        sys.stderr.write(f"{msg}\n")
        if code > 0:
            sys.exit(code)

    def __get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except configparser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s',
                              section, option)
        except configparser.NoSectionError:
            self.logger.debug('=> config file missing section %s', section)
        return None
