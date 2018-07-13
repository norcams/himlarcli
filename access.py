#!/usr/bin/env python

import json
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
ksclient.set_domain('dataporten')
logger = ksclient.get_logger()
mqclient = MQclient(options.config, debug=options.debug, log=logger)
mqclient.set_dry_run(options.dry_run)

# pylint: disable=W0613
def process_action(ch, method, properties, body): #callback
    print " [x] Received %r" % body
    ch.basic_ack(delivery_tag=method.delivery_tag)

    data = json.loads(body)
    user = ksclient.get_user_by_email(data['email'], user_type='api') #user_type='api'

    if user:
        if data['action'] == 'reset_password':
            print "=> Reset: "
            reset = ksclient.reset_password(email=data['email'], password=data['password'])
        elif data['action'] == 'provision':
            print "User exists! "
            pass
    else:
        if data['action'] == 'provision':
            print "=> Provisin: "
            provision = ksclient.provision_dataporten(email=data['email'], password=data['password'])
        elif data['action'] =='reset_password':
            print "Provisioning is required! "
            pass

def action_pop():
    channel = mqclient.get_channel('access')
    channel.basic_consume(process_action, queue='access')

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

# receiver
