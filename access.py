#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.mqclient import MQclient
from himlarcli.printer import Printer
from himlarcli import utils as himutils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()
mqclient = MQclient(options.config, debug=options.debug, log=logger)
mqclient.set_dry_run(options.dry_run)

# pylint: disable=W0613
def create_user(ch, method, properties, body):
    print " [x] Received %r" % body
    ch.basic_ack(delivery_tag=method.delivery_tag)

def action_pop():
    channel = mqclient.get_channel('access')
    channel.basic_consume(create_user, queue='access')

    print' [*] Waiting for messages. To exit press CTRL+C'

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    mqclient.close_connection()

def action_push():
    mqclient.push(email=options.email, password=options.password, queue='access')

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action() # pylint: disable=E1102
