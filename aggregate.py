#!/usr/bin/env python
import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils
from himlarcli.notify import Notify
from email.mime.text import MIMEText

desc = 'Mange host aggregate groups of compute nodes'
actions = ['show', 'instances', 'users', 'notify']
opt_args = { '-a': { 'dest': 'aggregate', 'help': 'aggregate name', 'required': True, 'metavar': 'name'} }

options = utils.get_action_options(desc, actions, opt_args=opt_args, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
domain='Dataporten'

if options.action[0] == 'show':
    pp = pprint.PrettyPrinter(indent=1)
    aggregate = novaclient.get_aggregate(options.aggregate)
    pp.pprint(aggregate.to_dict())
elif options.action[0] == 'instances':
    instances = novaclient.get_instances(options.aggregate, simple=True)
    for instance in instances:
        print instance
elif options.action[0] == 'users':
    users = novaclient.get_users(options.aggregate, simple=True)
    for user in users:
        print user
elif options.action[0] == 'notify':
    users = dict()
    instances = novaclient.get_instances(options.aggregate)
    # Generate instance list per user
    for i in instances:
        user = ksclient.get_user(i.user_id)
        if "@" not in user.name:
            continue
        email = user.name.lower()
        if email not in users:
            users[email] = dict()
        users[email][i.name] = { 'status': i.status }
    notify = Notify(options.config, debug=options.debug)
    with open('misc/notify_email.txt', 'r') as body_txt:
        body_content = body_txt.read()
    # Email each users
    for user, instances in users.iteritems():
        user_instances = ""
        for server,info in instances.iteritems():
            user_instances += "%s (%s)\n" % (server, info['status'])
        msg = MIMEText(user_instances + body_content)
        msg['Subject'] = 'UH-IaaS: Rebooting instance(s) (%s)' % ksclient.region
        #if not options.dry_run:
            #notify.send_mail(user, msg)
    pp = pprint.PrettyPrinter(indent=1)
    pp.pprint(users)
