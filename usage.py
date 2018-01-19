#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()

if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    himutils.sys_error('no valid regions found!')

def action_volume():
#    if options.filter and options.filter != 'all':
#        search_filter['type'] = options.filter
#    projects = ksclient.get_projects(domain=options.domain, **search_filter)

    projects = ksclient.get_projects(domain=options.domain)
    for region in regions:
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        # Quotas
        quotas = dict({'in_use': 0, 'quota': 0})
        for project in projects:
            quota = cinderclient.list_quota(project_id=project.id, usage=True)
            quotas['in_use'] += quota['gigabytes']['in_use']
            quotas['quota'] += quota['gigabytes']['limit']
        # Pools
        client = cinderclient.get_client()
        pools = client.volumes.get_pools(detail=True)
        tmp = pools.to_dict()
        out_pools = dict()
        out_pools['total_capacity_gb'] = tmp['pools'][0]['capabilities']['total_capacity_gb']
        out_pools['free_capacity_gb'] = tmp['pools'][0]['capabilities']['free_capacity_gb']
        out_pools['used_in_volume_gb'] = quotas['in_use']
        out_pools['total_quota_gb'] = quotas['quota']
        printer.output_dict({'header': '%s volumes' % region})
        printer.output_dict(out_pools)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
