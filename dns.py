#!/usr/bin/env python
""" Setup designate DNS """

import utils
from himlarcli.designate import Designate
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Input args
desc = 'Manage designate'
actions = ['show', 'create']
# Example opt_args (see utils.py)
#opt_args = { '-n': { 'dest': 'name', 'help': 'flavor class (mandatory)', 'required': True },
#             '-p': { 'dest': 'project', 'help': 'project to grant or revoke access'} }
opt_args = {}
options = utils.get_action_options(desc, actions, dry_run=True, opt_args=opt_args)
dns = Designate(options.config, debug=options.debug)


if options.action[0] == 'show':
    if options.dry_run:
        print 'DRY-RUN: show'
    else:
        print 'show'
elif options.action[0] == 'create':
    if options.dry_run:
        print 'DRY-RUN: create'
    else:
        print 'create'
