#!/usr/bin/env python

import sys
import utils
from himlarcli import logger
from himlarcli.state import State
from himlarcli.nova import Nova

print "Depricated!"
sys.exit(1)

desc = 'Update state information'
actions = ['purge','dump','save', 'start']

options = utils.get_host_action_options(desc, actions, False)
novaclient = Nova(options.config, debug=options.debug)
logger = novaclient.get_logger()
state = State(options.config, debug=options.debug, log=logger)

if options.action[0] == 'save':
    novaclient.save_states()
if options.action[0] == 'start':
    novaclient.start_instances_from_state()
elif options.action[0] == 'dump':
    instances = state.get_instances()
    for i in instances:
        print i
    state.close()
elif options.action[0] == 'purge':
    q = "Delete all state information (yes|no)? "
    answer = raw_input(q)
    if answer.lower() == 'yes':
        state = State(options.config, debug=options.debug)
        print "We are now purging all state info"
        state.purge()
        state.close()
    else:
        print "Purge aborted!"
