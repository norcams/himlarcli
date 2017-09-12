#!/usr/bin/env python

import sys
from himlarcli.keystone import Keystone
from himlarcli.cinder import Cinder
from himlarcli.nova import Nova
from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
regions = ksclient.find_regions(region_name=options.region)

if not regions:
    himutils.sys_error('no regions found!')

def action_show():
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        components = {'nova': novaclient, 'cinder': cinderclient, 'neutron': neutronclient}
        for comp, client in components.iteritems():
            if options.service != 'all' and comp != options.service:
                continue
            if hasattr(client, 'get_quota_class'):
                current = getattr(client, 'get_quota_class')()
            else:
                logger.debug('=> function get_quota_class not found for %s' % comp)
                continue
            if not isinstance(current, dict):
                current = current.to_dict()
            current['header'] = 'Quota for %s in %s' % (comp, region)
            printer.output_dict(current)

def action_update():
    dry_run_txt = 'DRY-RUN: ' if options.dry_run else ''
    defaults = himutils.load_config('config/quotas/%s' % options.quota_config, logger)
    if not defaults:
        himutils.sys_error('No default quotas found in config/quota/%s' % options.quota_config)
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        components = {'nova': novaclient, 'cinder': cinderclient, 'neutron': neutronclient}
        for comp, client in components.iteritems():
            if options.service != 'all' and comp != options.service:
                continue
            if comp not in defaults:
                logger.debug('=> could not find quota for %s in config' % comp)
                continue
            if hasattr(client, 'get_quota_class'):
                current = getattr(client, 'get_quota_class')()
            else:
                logger.debug('=> function get_quota_class not found for %s' % comp)
                continue
            if not isinstance(current, dict):
                current = current.to_dict()
            updates = dict()
            for k, v in defaults[comp].iteritems():
                if k in current and current[k] != v:
                    logger.debug("=> %sUpdated %s: from %s to %s in %s" %
                                 (dry_run_txt, k, current[k], v, region))
                    updates[k] = v
            if updates and not options.dry_run:
                result = getattr(client, 'update_quota_class')(updates=updates)
                logger.debug('=> %s' % result)
            elif not updates:
                logger.debug('=> no need to update default quota for %s in %s' % (comp, region))

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
