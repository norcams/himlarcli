#!/usr/bin/env python

import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Input args
desc = 'Manage flavors'
actions = ['update', 'purge', 'list', 'grant', 'revoke']
opt_args = {'-n': {'dest': 'name', 'help': 'flavor class (mandatory)', 'required': True},
            '-p': {'dest': 'project', 'help': 'project to grant or revoke access'}}

options = utils.get_action_options(desc, actions, dry_run=True, opt_args=opt_args)
ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=logger)
domain = 'Dataporten'

if options.action[0] == 'list':
    pp = pprint.PrettyPrinter(indent=1)
    flavors = novaclient.get_flavors(filters=options.name)
    for flavor in flavors:
        #print flavor.__dict__.keys()
        if not getattr(flavor, 'OS-FLV-DISABLED:disabled'):
            public = 'public' if getattr(flavor, 'os-flavor-access:is_public') else 'not public'
            print '------------------------'
            print '%s (%s):' % (flavor.name, public)
            print 'ram:   %s' % flavor.ram
            print 'vcpus: %s' % flavor.vcpus
            print 'disk:  %s' % flavor.disk
        else:
            print '------------------------'
            print '%s is disabled!' % flavor.name
        #pp.pprint(flavor.to_dict())
elif options.action[0] == 'update':
    flavors = himutils.load_config('config/flavors/%s.yaml' % options.name, logger)
    if not flavors:
        print 'ERROR! No flavors found in config/flavors/%s.yaml' % options.name
        sys.exit(1)
    print 'Update %s flavors' % options.name
    public = flavors['public'] if 'public' in flavors else False
    for name, spec in sorted(flavors[options.name].iteritems()):
        novaclient.update_flavor(name, spec, public, options.dry_run)
elif options.action[0] == 'purge':
    flavors = himutils.load_config('config/flavors/%s.yaml' % options.name, logger)
    if not flavors:
        print 'ERROR! No flavors found in config/flavors/%s.yaml' % options.name
        sys.exit(1)
    print 'Purge %s flavors' % options.name
    novaclient.purge_flavors(options.name, flavors, options.dry_run)
elif options.action[0] == 'grant' or options.action[0] == 'revoke':
    flavors = himutils.load_config('config/flavors/%s.yaml' % options.name, logger)
    if 'public' in flavors and flavors['public']:
        print 'Grant or revoke will not work on public flavors!'
        sys.exit(0)
    if not options.project:
        print 'Missing project to grant access'
        sys.exit(0)
    project = ksclient.get_project(options.project, domain=domain)
    if not project:
        print 'Could not find project %s' % options.project
        sys.exit(0)
    print "%s access to %s for %s" % (options.action[0], options.name, options.project)
    novaclient.update_flavor_access(filters=options.name,
                                    project_id=project.id,
                                    action=options.action[0],
                                    dry_run=options.dry_run)
