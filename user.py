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

desc = 'Mange users and user grups'
actions = ['list','show','delete']
opt_args = { '-n': { 'dest': 'user', 'help': 'user email (case sensitive)', 'required': False } }
#             '-m': { 'dest': 'date', 'help': 'date message', 'default': date, 'metavar': 'date'} }

options = utils.get_action_options(desc, actions, opt_args=opt_args, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
domain='Dataporten'

if options.action[0] == 'show':
    if not ksclient.is_valid_user(user=options.user, domain=domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    pp = pprint.PrettyPrinter(indent=1)
    obj = ksclient.get_user_objects(email=options.user, domain=domain)
    obj_types = [ 'api', 'dataporten', 'group', 'projects']
    for type in obj_types:
        if type not in obj:
            continue
        print "\n%s:\n---------" % type.upper()
        if type == 'projects':
            for project in obj[type]:
                pp.pprint(project.to_dict())
                print "\n"
        else:
            pp.pprint(obj[type].to_dict())
elif options.action[0] == 'list':
    users = ksclient.list_users(domain=domain)
    domains = dict()
    print "\nRegistered users:"
    print "-----------------"
    for user in users:
        if '@' in user:
            print user
            org = user.split("@")[1]
            if org in domains:
                domains[org] += 1
            else:
                domains[org] = 1
    print "\nEmail domains:"
    print "--------------"
    for k,v in domains.iteritems():
        print '%s = %s' % (k, v)
elif options.action[0] == 'delete':
    if not ksclient.is_valid_user(user=options.user, domain=domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    q = "Delete user and all instances for %s (yes|no)? " % options.user
    answer = raw_input(q)
    if answer.lower() == 'yes':
        print "We are now deleting user, project and instances for %s" % options.user
        print 'Please wait...'
        ksclient.delete_user(email=options.user, domain=domain, dry_run=options.dry_run)
    else:
        print "You just dodged a bullet my friend!"
