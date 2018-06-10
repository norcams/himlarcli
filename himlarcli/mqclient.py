import json
import pika
import himlarcli.utils as utils
import ConfigParser

class MQclient(object):

    def __init__(self, config_path, debug, log=None):
        self.config = utils.get_config(config_path)
        self.logger = utils.get_logger(__name__, self.config, debug, log)
        self.logger.debug('=> config file: %s', config_path)
        self.dry_run = False
        self.debug = debug
        credentials = pika.PlainCredentials(
            username=self.__get_config('rabbitmq', 'username'),
            password=self.__get_config('rabbitmq', 'password'))

        parameters = pika.ConnectionParameters(
            host=self.__get_config('rabbitmq', 'host'),
            virtual_host=self.__get_config('rabbitmq', 'vhost'),
            credentials=credentials)
        self.connection = pika.BlockingConnection(parameters)

    def set_dry_run(self, dry_run):
        self.logger.debug('=> set dry_run to %s in %s' % (dry_run, type(self).__name__))
        self.dry_run = True if dry_run else False

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
            result = channel.basic_publish(exchange='',
                                           routing_key=queue,
                                           body=message,
                                           properties=pika.BasicProperties(
                                               delivery_mode=2))
            if result:
                self.logger.debug('=> message %s added to queue %s', message, queue)
        else:
            self.logger.debug('=> DRY-RUN: message %s added to queue %s', message, queue)


    def __get_config(self, section, option):
        try:
            value = self.config.get(section, option)
            return value
        except ConfigParser.NoOptionError:
            self.logger.debug('=> config file section [%s] missing option %s',
                              section, option)
        except ConfigParser.NoSectionError:
            self.logger.debug('=> config file missing section %s', section)
        return None

# sender
