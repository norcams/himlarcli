#!/usr/bin/env python

import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.cinder import Cinder
from himlarcli.nova import Nova
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Input args
desc = 'Manage flavors'
actions = ['update-default', 'show-default']
opt_args = { '-n': { 'dest': 'name', 'help': 'project name'},
             '-p': { 'dest': 'project', 'help': 'project to grant or revoke access'} }
opt_args = {}

options = utils.get_action_options(desc, actions, dry_run=True, opt_args=opt_args)
ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=logger)
cinderclient = Cinder(options.config, debug=options.debug, log=logger)
domain='Dataporten'
components = { 'nova': novaclient, 'cinder': cinderclient }

if options.action[0] == 'show-default':
    pp = pprint.PrettyPrinter(indent=2)
    for comp, client in components.iteritems():
        if hasattr(client, 'get_quota_class'):
            current = getattr(client, 'get_quota_class')()
        else:
            print 'function get_quota_class not found for %s' % comp
            continue
        print "Current defaults for %s" % comp
        pp.pprint(current.to_dict())
elif options.action[0] == 'update-default':
    dry_run_txt = 'DRY-RUN: ' if options.dry_run else ''
    pp = pprint.PrettyPrinter(indent=2)
    defaults = himutils.load_config('config/quotas/default.yaml', logger)
    if not 'cinder' in defaults or not 'nova' in defaults:
        print 'ERROR! Default quotas found in config/quotas/default.yaml'
        sys.exit(1)
    for comp, client in components.iteritems():
        if hasattr(client, 'get_quota_class'):
            current = getattr(client, 'get_quota_class')()
        else:
            print 'function get_quota_class not found for %s' % comp
            continue
        updates = dict()
        for k,v in defaults[comp]['default'].iteritems():
            if getattr(current, k) != v:
                logger.debug("=> %sUpdated %s: from %s to %s" %
                             (dry_run_txt, k, getattr(current, k), v))
                updates[k] = v
        if updates:
            if not options.dry_run:
                print 'Updated defaults for %s quota:' % comp
                result = getattr(client, 'update_quota_class')(updates=updates)
                pp.pprint(result.to_dict())
        else:
            print 'Nothing to update for %s' % comp
