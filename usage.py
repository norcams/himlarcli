#!/usr/bin/env python

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
import re

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
    file = open('instanceslist.txt', 'w')
    for region in regions:
        flavors = dict()
        cores = ram = 0
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        for i in instances:
            flavor = novaclient.get_by_id('flavor', i.flavor['id'])
            if not flavor:
                himutils.sys_error('Flavor with ID %s not found' % i.flavor['id'], 0)
                continue
            flavors[flavor.name] = flavors.get(flavor.name, 0) + 1
            cores += flavor.vcpus
            ram += flavor.ram

            # Check which flavor each instance uses and write the result to a file
            flavoritems = (flavors.keys())
            project = ksclient.get_by_id('project', i.tenant_id)
            instance = novaclient.get_instance(i)
            d = re.compile("^d1.*")
            m = re.compile("^m2.*")
            dlist = filter(d.match, flavoritems)
            mlist = filter(m.match, flavoritems)
            if project:
                if dlist:
                    file.write('---------------------------------------------------------------\n')
                    file.write('Flavor: (flavor name, instance name, project name, project id) \n')
                    file.write('---------------------------------------------------------------\n')
                    file.write(flavor.name   + '\n')
                    file.write(instance.name + '\n')
                    file.write(project.name  + '\n')
                    file.write(project.id    + '\n')
                    file.write('---------------------------------------------------------------\n')
                elif mlist:
                    file.write('---------------------------------------------------------------\n')
                    file.write('Flavor: (flavor name, instance name, project name, project id) \n')
                    file.write('---------------------------------------------------------------\n')
                    file.write(flavor.name   + '\n')
                    file.write(instance.name + '\n')
                    file.write(project.name  + '\n')
                    file.write(project.id    + '\n')
                    file.write('---------------------------------------------------------------\n')
                else:
                    pass

        printer.output_dict({'header': '%s instances' % region})
        printer.output_dict(flavors)
        printer.output_dict({'header': '%s resources' % region})
        printer.output_dict({'cores': cores, 'ram': '%.1f MB' % int(ram)})
    file.close()

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
