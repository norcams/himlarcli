#!/usr/bin/env python

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils

# We need to preload default config to set default region
# This will NOT work with custom config file args!
config = utils.get_himlarcli_config(None)

parser = Parser()
parser.update_default('--region', utils.get_config_entry(config, 'openstack', 'region'))
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# This script will only work on one region
region = options.region

def action_list():
    nc = utils.get_client(Neutron, options, logger, region)
    networks = nc.list_networks()
    printer.output_dict({'header': 'networks (name, shared, IPv4 addresses)'})
    for net in networks:
        output = {
            '0': net['name'],
            '1': net['shared'],
            '2': nc.get_allocation_pool_size(network_id=net['id'], ip_version=4)
        }
        printer.output_dict(output, sort=True, one_line=True)

def action_show_access():
    nc = utils.get_client(Neutron, options, logger, region)
    net = nc.get_network_by_name(options.network)
    policies = nc.get_rbac_policies(object_type='network', object_id=net['id'])
    printer.output_dict({'header': f'project access to {options.network} network (id, name)'})
    for p in policies['rbac_policies']:
        project = kc.get_by_id('project',  p['target_tenant'])

        output = {
            '0': p['target_tenant'],
            '1': project.name if project else 'None'
        }
        printer.output_dict(output, sort=True, one_line=True)

def action_grant():
    nc = utils.get_client(Neutron, options, logger, region)
    net = nc.get_network_by_name(options.network)
    project = kc.get_project_by_name(options.project)
    if nc.grant_rbac_policy(project.id, net['id']):
        printer.output_msg(f'{options.project} granted access to network {options.network}')
    else:
        printer.output_msg(f'Could not grant access. Check if access already exists in {region}')

def action_revoke():
    nc = utils.get_client(Neutron, options, logger, region)
    net = nc.get_network_by_name(options.network)
    project = kc.get_project_by_name(options.project)
    if nc.revoke_rbac_policy(project.id, net['id']):
        printer.output_msg(f'Access revoked for {options.project} to {options.network}')
    else:
        printer.output_msg('Could not revoke access. Check if access already exists')

def action_public_ipv4():
    nc = utils.get_client(Nova, options, logger, region)
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
        if len(list(i.addresses.keys())) > 0:
            network = list(i.addresses.keys())[0]
        else:
            network = 'unknown'
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
    utils.sys_error(f"Function action_{options.action}() not implemented")
action()
