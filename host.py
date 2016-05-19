#!/usr/bin/python

import sys
import pprint
import utils
from himlarcli.nova import Nova

desc = 'Perform action on all instances on host'
actions = ['print','start','stop','delete','instance']

options = utils.get_action_options(desc, actions)
novaclient = Nova(options.config, options.host)

if options.action[0] == 'print':
    emails = novaclient.list_users()
    for i in emails:
        print i
elif options.action[0] == 'instance':
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(novaclient.list_instances())
elif options.action[0] == 'start':
    novaclient.start_instances()
elif options.action[0] == 'stop':
    novaclient.stop_instances()
elif options.action[0] == 'delete':
    q = "Delete all stopped instances on %s (yes|no)? " % options.host
    answer = raw_input(q)
    if answer.lower() == 'yes':
        print "We are now deleting all instances"
        novaclient.delete_instances()
    else:
        print "You just dodged a bullet my friend!"
