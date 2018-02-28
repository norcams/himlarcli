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
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        # Quotas
        quotas = dict({'in_use': 0, 'quota': 0})
        for project in projects:
            # Filter demo
            if not options.demo and project.type == 'demo':
                continue
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
        out_pools['used_in_volume_gb'] = float(quotas['in_use'])
        out_pools['total_quota_gb'] = float(quotas['quota'])
        printer.output_dict({'header': '%s volumes' % region})
        printer.output_dict(out_pools)

def action_instance():
    file = open('flavorm2d1.txt', 'w')
    for region in regions:
        flavors = dict()
        cores = ram = 0
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        projects = dict()
        for i in instances:
            flavor = novaclient.get_by_id('flavor', i.flavor['id'])
            if not flavor:
                himutils.sys_error('Flavor with ID %s not found' % i.flavor['id'], 0)
                continue
            flavors[flavor.name] = flavors.get(flavor.name, 0) + 1
            cores += flavor.vcpus
            ram += flavor.ram
            # Check which project uses d1 or m2 flavor type
            project = ksclient.get_by_id('project', i.tenant_id)
            if 'm2' in flavor.name or 'd1' in flavor.name:
                if project.name not in projects:
                    projects[project.name] = dict({'m2': False, 'd1': False})
                projects[project.name]['m2'] = True if 'm2' in flavor.name else False
                projects[project.name]['d1'] = True if 'd1' in flavor.name else False
        printer.output_dict({'header': '%s instances' % region})
        printer.output_dict(flavors)
        printer.output_dict({'header': '%s resources' % region})
        printer.output_dict({'cores': cores, 'ram': '%.1f MB' % int(ram)})
        # Write the result to a file
        for key, value in projects.iteritems():
            if value['m2']:
                file.write('./flavor.py grant -n m2 -p' + key + '\n')
            if value['d1']:
                file.write('./flavor.py grant -n d1 -p' + key + '\n')
    file.close()

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
