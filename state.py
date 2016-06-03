#!/usr/bin/env python

import sys
import utils
from himlarcli import logger
from himlarcli.state import State
from himlarcli.nova import Nova

desc = 'Update state information'
actions = ['purge','dump','save', 'start']

options = utils.get_host_action_options(desc, actions, False)

if options.action[0] == 'save':
    novaclient = Nova(options.config, debug=options.debug)
    novaclient.save_states()
if options.action[0] == 'start':
    novaclient = Nova(options.config, debug=options.debug)
    novaclient.start_instances_from_state()
elif options.action[0] == 'dump':
    state = State(options.config, debug=options.debug)
    state.get_instances()
    state.close()
elif options.action[0] == 'purge':
    q = "Delete all state information (yes|no)? "
    answer = raw_input(q)
    if answer.lower() == 'yes':
        state = State(options.config, debug=options.debug)
        print "We are now purgin all state info"
        state.purge()
        state.close()
    else:
        print "Purge aborted!"
