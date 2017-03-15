#!/usr/bin/env python
import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Input args
desc = 'Instance stats'
actions = ['type']
opt_args = {}
options = utils.get_action_options(desc, actions, opt_args=opt_args, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
domain='Dataporten'

# Regions
regions = himutils.load_region_config('config/stats',
                                      region=ksclient.region,
                                      log=logger)

if options.action[0] == 'type':
    stats = { 'personal': 0, 'research': 0, 'education': 0, 'admin': 0, 'test': 0 }
    for name, info in sorted(regions['regions'].iteritems()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()

        for i in instances:
            project = ksclient.get_project_by_id(i.tenant_id)
            if hasattr(project, 'course'):
                stats['education'] += 1
            elif '@' in project.name:
                stats['personal'] += 1
            else:
                if hasattr(project, 'type'):
                    stats[project.type] += 1
                else:
                    stats['admin'] += 1
    print "\nUsage grouped by type:"
    print "----------------------"
    for s in sorted(stats):
        print "%s = %s" % (s, stats[s])
