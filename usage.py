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
    projects = ksclient.get_projects(domain=options.domain)
    for region in regions:
        cc = himutils.get_client(Cinder, options, logger, region)

        # Quotas
        quotas = dict({'in_use': 0, 'quota': 0})
        for project in projects:
            if not hasattr(project, "type"): # unknown project type
              logger.debug('=> unknow project type %s', project.name)
              continue
            # Filter demo
            if not options.demo and project.type == 'demo':
                continue
            quota = cc.get_quota(project_id=project.id, usage=True)
            quotas['in_use'] += quota['gigabytes']['in_use']
            quotas['quota'] += quota['gigabytes']['limit']
        # Pools
        pools = cc.get_pools(detail=True)
        tmp = pools.to_dict()
        for pool in pools.pools:
            name = pool['capabilities']['volume_backend_name']
            #print pool
            out_pool = dict()
            out_pool['total_capacity_gb'] = pool['capabilities']['total_capacity_gb']
            out_pool['free_capacity_gb'] = pool['capabilities']['free_capacity_gb']
            printer.output_dict({'header': '%s pool %s' % (region, name)})
            printer.output_dict(out_pool)
        out_pools = dict()
        out_pools['used_in_volume_gb'] = float(quotas['in_use'])
        out_pools['total_quota_gb'] = float(quotas['quota'])
        printer.output_dict({'header': '%s openstack volumes' % region})
        printer.output_dict(out_pools)

def action_instance():
    #ToDo
    for region in regions:
        flavors = dict()
        cores = ram = 0
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        total = 0
        for i in instances:
            # Filter demo
            project = ksclient.get_by_id('project', i.tenant_id)
            if not options.demo and project and 'DEMO' in project.name:
                continue
            flavor_name = i.flavor.get('original_name', 'unknown')
            flavors[flavor_name] = flavors.get(flavor_name, 0) + 1
            cores += i.flavor.get('vcpus', 0)
            ram += i.flavor.get('ram', 0)
            total += 1
        printer.output_dict({'header': '%s instances' % region})
        printer.output_dict(flavors)
        printer.output_dict({'header': '%s resources' % region})
        printer.output_dict({'cores': cores,
                             'ram': '%.1f MB' % int(ram),
                             'instances': total})

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
