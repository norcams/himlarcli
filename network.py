#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
import time


parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
nc = Nova(options.config, debug=options.debug, log=logger)
nc.set_dry_run(options.dry_run)

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()

def action_list():
    for region in regions:
        nc = himutils.get_client(Neutron, options, logger, region)
        networks = nc.list_networks()
        printer.output_dict({'header': 'networks (name, shared, IPv4 addresses)'})
        for net in networks:
            output = {
                '0': net['name'],
                '1': net['shared'],
                '2': nc.get_allocation_pool_size(network_id=net['id'], ip_version=4)
            }
            printer.output_dict(output, sort=True, one_line=True)

def action_dualstack():
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        instances = nc.get_all_instances()
        printer.output_dict({'header': 'Instance list (id, name, status, updated)'})
        status = dict({'total': 0})
        for i in instances:
            # Filter for project type
            if options.type:
                project = kc.get_by_id('project', i.tenant_id)
                if hasattr(project, 'type') and project.type != options.type:
                    status['type'] = options.type
                    continue
            network = i.addresses.keys()[0] if len(i.addresses.keys()) > 0 else 'unknown'
            if network != 'dualStack':
                continue
            output = {
                '1': i.id,
                '3': i.name,
                '4': i.status,
                #'2': i.updated,
                #'6'': getattr(i, 'OS-EXT-SRV-ATTR:instance_name'),
                #'5': i.flavor['original_name']
                '7': network
            }
            printer.output_dict(output, sort=True, one_line=True)
            status['total'] += 1
            status[str(i.status).lower()] = status.get(str(i.status).lower(), 0) + 1
        printer.output_dict({'header': 'Counts'})
        printer.output_dict(status)


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
