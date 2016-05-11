#!/usr/bin/python

import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone

options = utils.get_options(sys.argv[1:], sys.argv[0])
novaclient = Nova(options['config'], options['host'])

if options['action'] == 'print':
    print novaclient.list_users()
elif options['action'] == 'start':
    novaclient.start_instances()
elif options['action'] == 'stop':
    novaclient.stop_instances()
#elif options['action'] == 'delete':
#    novaclient.delete_instances()
else:
    print "action must be one of print, start, stop or delete"
