#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
nc = Nova(options.config, debug=options.debug, log=logger)
nc.set_dry_run(options.dry_run)


def action_instances():
    host = nc.get_host(nc.get_fqdn(options.host))
    if not host:
        himutils.sys_error('Could not find valid host %s' % options.host)
    search_opts = dict(all_tenants=1, host=host.hypervisor_hostname)
    instances = nc.get_all_instances(search_opts=search_opts)
    printer.output_dict({'header': 'Instance list (id, name, status, updated)'})
    status = dict({'total': 0})
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
    instances = nc.get_instances(host=hostname)
    if instances:
        himutils.sys_error('Host %s not empty. Remove instances first' % hostname)
    if nc.move_host_aggregate(hostname=hostname, aggregate=options.aggregate):
        print "Host %s moved to aggregate %s" % (hostname, options.aggregate)

def action_enable():
    host = nc.get_host(hostname=nc.get_fqdn(options.host), detailed=True)
    if not host:
        himutils.sys_error('Could not find valid host %s' % options.host)
    if host.status != 'enabled' and not options.dry_run:
        nc.enable_host(host.hypervisor_hostname)
        print 'Host %s enabled' % host.hypervisor_hostname

def action_disable():
    host = nc.get_host(hostname=nc.get_fqdn(options.host), detailed=True)
    if not host:
        himutils.sys_error('Could not find valid host %s' % options.host)
    if host.status != 'disabled' and not options.dry_run:
        nc.disable_host(host.hypervisor_hostname)
        print 'Host %s disabled' % host.hypervisor_hostname

def action_list():
    aggregates = nc.get_all_aggregate_hosts()
    if options.aggregate == 'all':
        hosts = nc.get_hosts()
    else:
        hosts = nc.get_aggregate_hosts(options.aggregate, True)
    header = {'header': 'Hypervisor list (name, aggregate, vms, vcpu_used,' +
                        'ram_gb_used, state, status)'}
    printer.output_dict(header)
    for host in hosts:
        output = {
            '1': host.hypervisor_hostname,
            '6': host.state,
            '7': host.status,
            '3': host.running_vms,
            '4': host.vcpus_used,
            '5': int(host.memory_mb_used/1024),
            '2': aggregates.get(host.hypervisor_hostname, 'unknown')
        }
        printer.output_dict(output, sort=True, one_line=True)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
