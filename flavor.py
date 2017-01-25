#!/usr/bin/env python

import sys
import utils
import pprint
from himlarcli.nova import Nova
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Input args
desc = 'Manage flavors'
actions = ['update', 'purge', 'list']
opt_args = { '-n': { 'dest': 'name', 'help': 'flavor class (mandatory)', 'required': True } }
#             '-u': { 'dest': 'user', 'help': 'email of teacher', 'metavar': 'user'},
#             '-q': { 'dest': 'quota', 'help': 'project quota', 'default': 'course', 'metavar': 'quota'},
#             '-t': { 'dest': 'type', 'help': 'flavor type (default m1)', 'default': 'm1'} }

options = utils.get_action_options(desc, actions, dry_run=True, opt_args=opt_args)
novaclient = Nova(options.config, debug=options.debug)
logger = novaclient.get_logger()
#defaults = himutils.load_config('config/flavors/default.yaml', logger)

if options.action[0] == 'list':
    pp = pprint.PrettyPrinter(indent=1)
    flavors = novaclient.get_flavors(filter=options.name)
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
#elif options.action[0] == 'show':
#
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
    novaclient.purge_flavors(options.name, flavors)
