#!/usr/bin/env python
""" Update nova flavors """

import sys
import utils
from himlarcli.nova import Nova
from himlarcli import utils as himutils

options = utils.get_options('Create and update nova flavors',
                             hosts=0, dry_run=True)
novaclient = Nova(options.config, debug=options.debug)
logger = novaclient.get_logger()

flavors = himutils.load_config('config/flavor.yaml', logger)

if not 'default' in flavors:
    print "Missing default in config/flavor.yaml"
    sys.exit(1)

for name, spec in flavors['default'].iteritems():
    novaclient.update_flavor(name, spec, options.dry_run)

if options.debug:
    print "---------DEBUG ONLY--------------"
    print 'Complete list of flavors in use:'

    for i in novaclient.get_flavors():
        print i._info
