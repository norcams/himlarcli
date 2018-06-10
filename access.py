#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.mqclient import MQclient
from himlarcli.printer import Printer
from himlarcli import utils as himutils

import json

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()
mqclient = MQclient(options.config, debug=options.debug, log=logger)
mqclient.set_dry_run(options.dry_run)

# pylint: disable=W0613
def process_action(ch, method, properties, body): #callback

    print " [x] Received %r" % body
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # check action if reset or provision
    data = json.loads(body)

    if data['action'] == 'reset_password':
        print "password"
        reset_password()
        #ksclient.update(email=data['email'], password=data['password'])

    if data['action'] == 'provision':
        print 'proooooo'
        print "-----------------"
        print data['action']
        print "-----------------"

        ksclient.create_user(domain=options.domain,
                         email=email,
                         admin=options.admin,
                         description=options.description,
                         enddate=str(enddate))



def reset_password(self):
    obj = dict()
    api = self.get_user_by_email(email=email, user_type='api')
    if not api:
        self.logger.warning('=> could not find api user for email %s' % email)
    dp = self.get_user_by_email(email=email, user_type='dp')
    if not dp:
        self.logger.warning('=> could not find dataporten user for email %s' % email)
    group = self.get_group_by_email(email)
    obj['api'] = api
    obj['dataporten'] = dp
    obj['group'] = group
    if 'api' in obj and obj['api']:
      #  self.logger.debug('=> reset password for user %s' % email)
        kclient.users.update(obj['api'], password=password)


def action_provision(body):
    # Reset password and update
    channel = mqclient.get_channel('access')
    up = channel.basic_consume(process_action, queue='access')
    obj = ksclient.get_user_objects(email=options.user, domain=options.domain)

    ksclient.create_user(domain=options.domain,
                         email=email,
                         admin=options.admin,
                         description=options.description,
                         enddate=str(enddate))

    data = json.loads(body)
    print data

#-----------------------------------------------------------------
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
