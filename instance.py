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
actions = ['type', 'user', 'org']
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
    total = 0
    for name, info in sorted(regions['regions'].iteritems()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()
        total += len(instances)
        for i in instances:
            project = ksclient.get_project_by_id(i.tenant_id)
            if hasattr(project, 'course'):
                stats['education'] += 1
            elif '@' in project.name:
                stats['personal'] += 1
            else:
                if hasattr(project, 'type'):
                    if project.type not in stats:
                        print "unknown project type %s for %s" % (project.type, project.name)
                    else:
                        stats[project.type] += 1
                else:
                    stats['admin'] += 1
    print "\nUsage grouped by type:"
    print "----------------------"
    for s in sorted(stats):
        share = (float(stats[s])/float(total))*100
        print "%s = %s (%.f%%)" % (s, stats[s], share)
elif options.action[0] == 'user':
    stats = dict()
    total = 0
    for name, info in sorted(regions['regions'].iteritems()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()
        total += len(instances)
        for i in instances:
            user = ksclient.get_user_by_id(i.user_id)
            org = user.name.split("@")[1]
            if org in stats:
                stats[org] += 1
            else:
                stats[org] = 1
    print "\nUsage grouped by user email domain:"
    print "-----------------------------------"
    for s in sorted(stats):
        share = (float(stats[s])/float(total))*100
        print "%s = %s (%.f%%)" % (s, stats[s], share)
elif options.action[0] == 'org':
    stats = dict()
    total = 0
    for name, info in sorted(regions['regions'].iteritems()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()
        total += len(instances)
        for i in instances:
            user = ksclient.get_user_by_id(i.user_id)
            domain = user.name.split("@")[1]
            org = domain.split(".")[-2]
            if org in stats:
                stats[org] += 1
            else:
                stats[org] = 1
    print "\nUsage grouped by user email domain:"
    print "-----------------------------------"
    for s in sorted(stats):
        share = (float(stats[s])/float(total))*100
        print "%s = %s (%.f%%)" % (s, stats[s], share)
