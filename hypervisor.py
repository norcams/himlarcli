#!/usr/bin/env python

from datetime import date
import re

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.color import Color
from himlarcli.placement import Placement

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
nc = Nova(options.config, debug=options.debug, log=logger)
nc.set_dry_run(options.dry_run)


#---------------------------------------------------------------------
# Main functions
#---------------------------------------------------------------------
def action_instances():
    host = nc.get_host(nc.get_fqdn(options.host))
    if not host:
        himutils.sys_error('Could not find valid host %s' % options.host)
    search_opts = dict(all_tenants=1, host=host.hypervisor_hostname)
    instances = nc.get_all_instances(search_opts=search_opts)

    if options.format == 'table':
        output = {}
        output['header'] = [
            'ID',
            'NAME',
            'PROJECT',
            'AGE',
            'STATUS',
            'FLAVOR',
        ]
        output['align'] = [
            'l',
            'l',
            'l',
            'r',
            'l',
            'l',
        ]
        output['sortby'] = 2
        counter = 0
        for i in instances:
            project = kc.get_by_id('project', i.tenant_id)
            # Filter for project type
            if options.type:
                if hasattr(project, 'type') and project.type != options.type:
                    status['type'] = options.type
                    continue
            created = himutils.get_date(i.created, None, '%Y-%m-%dT%H:%M:%SZ')
            active_days = (date.today() - created).days

            # status color
            if i.status == 'ACTIVE':
                instance_status = Color.fg.red + i.status + Color.reset
            elif i.status == 'SHUTOFF':
                instance_status = Color.fg.GRN + i.status + Color.reset
            elif i.status == 'PAUSED':
                instance_status = Color.fg.BLU + i.status + Color.reset
            else:
                instance_status = Color.fg.YLW + i.status + Color.reset

            # project color
            if project is None:
                project_name = Color.fg.red + "None" + Color.reset
            else:
                project_name = Color.fg.cyn + project.name + Color.reset

            output[counter] = [
                Color.dim + i.id + Color.reset,
                Color.fg.GRN + i.name + Color.reset,
                project_name,
                active_days,
                instance_status,
                Color.fg.WHT + i.flavor['original_name'] + Color.reset,
            ]
            counter += 1
        printer.output_dict(output, sort=True, one_line=False)
    else:
        printer.output_dict({'header': 'Instance list (id, name, status, updated)'})
        status = {'total': 0}
        for i in instances:
            # Filter for project type
            if options.type:
                project = kc.get_by_id('project', i.tenant_id)
                if hasattr(project, 'type') and project.type != options.type:
                    status['type'] = options.type
                    continue
            output = {
                '1': i.id,
                '3': i.name,
                '4': i.status,
                #'2': i.updated,
                #'6'': getattr(i, 'OS-EXT-SRV-ATTR:instance_name'),
                '5': i.flavor['original_name']
            }
            printer.output_dict(output, sort=True, one_line=True)
            status['total'] += 1
            status[str(i.status).lower()] = status.get(str(i.status).lower(), 0) + 1
        printer.output_dict({'header': 'Counts'})
        printer.output_dict(status)


def action_show():
    host = nc.get_host(hostname=nc.get_fqdn(options.host), detailed=True)
    if not host:
        himutils.sys_error('Could not find valid host %s' % options.host)
    printer.output_dict(host.to_dict())

def action_users():
    users = nc.get_users(options.aggregate, simple=True)
    printer.output_dict({'header': 'User in %s' % options.aggregate,
                         'users': list(users)})

def action_move():
    hostname = nc.get_fqdn(options.host)
    if nc.add_host_to_aggregate(hostname=hostname, aggregate_name=options.aggregate, move=True):
        himutils.info(f"Host {hostname} moved to aggregate {options.aggregate}")

def action_add():
    hostname = nc.get_fqdn(options.host)
    if nc.add_host_to_aggregate(hostname=hostname, aggregate_name=options.aggregate, move=False):
        himutils.info(f"Host {hostname} added to aggregate {options.aggregate}")

def action_remove():
    hostname = nc.get_fqdn(options.host)
    if nc.remove_host_from_aggregate(hostname=hostname, aggregate_name=options.aggregate):
        himutils.info(f"Host {hostname} removed from aggregate {options.aggregate}")

def action_enable():
    host = nc.get_host(hostname=nc.get_fqdn(options.host), detailed=True)
    if not host:
        himutils.fatal(f"Could not find valid host {options.host}")
    if host.status != 'enabled' and not options.dry_run:
        nc.enable_host(host.hypervisor_hostname)
        himutils.info(f"Host {host.hypervisor_hostname} enabled")

def action_disable():
    host = nc.get_host(hostname=nc.get_fqdn(options.host), detailed=True)
    if not host:
        himutils.fatal(f"Could not find valid host {options.host}")
    if host.status != 'disabled' and not options.dry_run:
        nc.disable_host(host.hypervisor_hostname)
        himutils.info(f"Host {host.hypervisor_hostname} disabled")

def action_list():
    aggregates = nc.get_all_aggregate_hosts()
    if options.aggregate == 'all':
        hosts = nc.get_hosts()
    else:
        hosts = nc.get_aggregate_hosts(options.aggregate, True)
    if options.format == 'table':
        output = {}
        if options.verbose:
            output['header'] = [
                'NAME',
                'AGGREGATES',
                'VMs',
                'VM states',
                'vCPUs',
                'MEMORY (GiB)',
                'DISK (GB)',
                'STATE',
                'STATUS',
            ]
            output['align'] = [
                'l',
                'l',
                'r',
                'r',
                'r',
                'r',
                'r',
                'l',
                'l',
            ]
        else:
            output['header'] = [
                'NAME',
                'AGGREGATES',
                'STATE',
                'STATUS',
            ]
            output['align'] = [
                'l',
                'l',
                'l',
                'l',
            ]
        output['sortby'] = 0
        counter = 0
        region = kc.get_config('openstack', 'region')
        for host in hosts:
            r_hostname = Color.fg.blu + re.sub('\.mgmt\..+?\.uhdc\.no$', '', host.hypervisor_hostname) + Color.reset
            r_aggregate = ','.join(aggregates.get(host.hypervisor_hostname, []))
            r_status = host.status.upper()
            if options.verbose:
                resource_usage = get_resource_usage(host.id, region)
                r_vcpus = f"{resource_usage['vcpu_used']} / {resource_usage['vcpu_max']} ({resource_usage['vcpu_allocation_ratio']})"
                r_mem = f"{resource_usage['memory_gb_used']} / {resource_usage['memory_gb_max']} ({resource_usage['memory_allocation_ratio']})"
                search_opts = dict(all_tenants=1, host=host.hypervisor_hostname)
                instances = nc.get_all_instances(search_opts=search_opts)
                r_vms = str(len(instances))
                r_vm_states = ''
                count = {
                    'active':  0,
                    'shutoff': 0,
                    'paused':  0,
                    'error':   0,
                    'other':   0,
                }
                for i in instances:
                    if i.status == 'ACTIVE':
                        count['active'] += 1
                    elif i.status == 'SHUTOFF':
                        count['shutoff'] += 1
                    elif i.status == 'PAUSED':
                        count['paused'] += 1
                    elif i.status == 'ERROR':
                        count['error'] += 1
                    else:
                        count['other'] += 1
                if count['active'] > 0:
                    r_vm_states += f"{Color.fg.grn}{count['active']}{Color.reset} "
                else:
                    r_vm_states += f"{Color.dim}-{Color.reset} "
                if count['shutoff'] > 0:
                    r_vm_states += f"{Color.fg.RED}{count['shutoff']:2d}{Color.reset} "
                else:
                    r_vm_states += f"{Color.dim} -{Color.reset} "
                if count['paused'] > 0:
                    r_vm_states += f"{Color.fg.blu}{count['paused']}{Color.reset} "
                else:
                    r_vm_states += f"{Color.dim}-{Color.reset} "
                if count['error'] > 0:
                    r_vm_states += f"{Color.bg.red}{Color.fg.wht}{Color.bold}{count['error']}{Color.reset} "
                else:
                    r_vm_states += f"{Color.dim}-{Color.reset} "
                if count['other'] > 0:
                    r_vm_states += f"{Color.fg.ylw}{count['other']}{Color.reset}"
                else:
                    r_vm_states += f"{Color.dim}-{Color.reset}"

                if re.search(r"^(central1|windows1|placeholder1|hpc1)$", r_aggregate):
                    r_disk = "-"
                else:
                    r_disk = f"{resource_usage['disk_gb_used']} / {resource_usage['disk_gb_max']} ({resource_usage['disk_allocation_ratio']})"

            if host.status == 'enabled':
                r_aggregate = Color.fg.ylw + r_aggregate + Color.reset
                r_status = Color.fg.GRN + r_status + Color.reset
            else:
                r_aggregate = Color.fg.YLW + r_aggregate + Color.reset
                r_status = Color.fg.red + r_status + Color.reset
                if options.verbose:
                    r_vcpus = Color.dim + r_vcpus + Color.reset
                    r_mem = Color.dim + r_mem + Color.reset
                    r_disk = Color.dim + r_disk + Color.reset
            if host.state == 'up':
                r_state = Color.fg.GRN + host.state.upper() + Color.reset
            else:
                r_state = Color.fg.red + host.state.upper() + Color.reset
            if options.verbose:
                output[counter] = [
                    r_hostname,
                    r_aggregate,
                    r_vms,
                    r_vm_states,
                    r_vcpus,
                    r_mem,
                    r_disk,
                    r_state,
                    r_status,
                ]
            else:
                output[counter] = [
                    r_hostname,
                    r_aggregate,
                    r_state,
                    r_status,
                ]
            counter += 1
        printer.output_dict(output, sort=True, one_line=False)
        print("-----")
        print(f"VM States: {Color.fg.grn}ACTIVE{Color.reset} ",
              f"{Color.fg.RED}SHUTOFF{Color.reset} ",
              f"{Color.fg.blu}PAUSED{Color.reset} ",
              f"{Color.bg.red}{Color.fg.wht}{Color.bold}ERROR{Color.reset} ",
              f"{Color.fg.ylw}other...{Color.reset}")
    else:
        header = {'header': 'Hypervisor list (name, aggregates, ' +
                  'state, status)'}
        printer.output_dict(header)
        for host in hosts:
            output = {
                '1': host.hypervisor_hostname,
                '2': ','.join(aggregates.get(host.hypervisor_hostname, 'unknown')),
                '3': host.state,
                '4': host.status,
            }
            printer.output_dict(output, sort=True, one_line=True)

#---------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------

def get_resource_usage(hypervisor_uuid:str, region:str):
    placement = Placement(kc, region)
    resource = placement.get_resource_provider_usages(hypervisor_uuid)
    inventory_vcpu   = placement.get_resource_provider_inventory(hypervisor_uuid, 'VCPU')
    inventory_memory = placement.get_resource_provider_inventory(hypervisor_uuid, 'MEMORY_MB')
    inventory_disk   = placement.get_resource_provider_inventory(hypervisor_uuid, 'DISK_GB')

    data = {
        "vcpu_used":               resource['usages']['VCPU'],
        "vcpu_max":                inventory_vcpu['max_unit'],
        "vcpu_allocation_ratio":   inventory_vcpu['allocation_ratio'],
        "memory_gb_used":          int(resource['usages']['MEMORY_MB'] / 1024),
        "memory_gb_max":           int(inventory_memory['max_unit'] / 1024),
        "memory_allocation_ratio": inventory_memory['allocation_ratio'],
        "disk_gb_used":            resource['usages']['DISK_GB'],
        "disk_gb_max":             inventory_disk['max_unit'],
        "disk_allocation_ratio":   inventory_disk['allocation_ratio'],
        }

    return data


# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
