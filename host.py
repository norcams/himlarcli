#!/usr/bin/python

import sys
import pprint
import utils
from himlarcli.nova import Nova

desc = 'Perform action on all instances on host'
actions = ['list','start','stop','delete']

options = utils.get_host_action_options(desc, actions)
novaclient = Nova(options.config, options.host, options.debug)

if options.action[0] == 'list':
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
