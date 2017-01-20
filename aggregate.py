#!/usr/bin/env python
import sys
import utils
import pprint
from datetime import datetime, timedelta
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils
from himlarcli.notify import Notify
from email.mime.text import MIMEText

himutils.is_virtual_env()

desc = 'Mange host aggregate groups of compute nodes. Note that notify sends email to users!'
actions = ['show', 'instances', 'users', 'notify']
# Default date for notify are today at 14:00 + 5 days
d = datetime.today()
date = datetime(d.year, d.month, d.day, 14, 0) + timedelta(days=5)
date = date.strftime('%Y-%m-%d around %H:00')
opt_args = { '-n': { 'dest': 'aggregate', 'help': 'aggregate name', 'required': True, 'metavar': 'name'},
             '-m': { 'dest': 'date', 'help': 'date message', 'default': date, 'metavar': 'date'} }

options = utils.get_action_options(desc, actions, opt_args=opt_args, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
domain='Dataporten'
msg_file='misc/notify_reboot.txt'

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
    if users:
        mapping = dict(region=ksclient.region.upper(), date=options.date)
        body_content = himutils.load_template(inputfile=msg_file,
                                              mapping=mapping,
                                              log=ksclient.get_logger())
        if not body_content:
            print 'ERROR! Could not find and parse mail body in %s' % options.msg
            sys.exit(1)
        notify = Notify(options.config, debug=options.debug)
    # Email each users
    for user, instances in users.iteritems():
        user_instances = ""
        for server,info in instances.iteritems():
            user_instances += "%s (current status %s)\n" % (server, info['status'])
        msg = MIMEText(user_instances + body_content)
        msg['Subject'] = 'UH-IaaS: Rebooting instance (%s)' % ksclient.region
        if not options.dry_run:
            notify.send_mail(user, msg)
            print "Sending email to user %s" % user
        else:
            print "Dry-run: Mail would be sendt to user %s" % user
    pp = pprint.PrettyPrinter(indent=1)
    print "\nComplete list of users and instances:"
    print "====================================="
    pp.pprint(users)
