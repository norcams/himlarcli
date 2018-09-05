#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
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


def action_instances():
    host = nc.get_host(nc.get_fqdn(options.host))
    if not host:
        himutils.sys_error('Could not find valid host %s' % options.host)
    search_opts = dict(all_tenants=1, host=host.hypervisor_hostname)
    instances = nc.get_all_instances(search_opts=search_opts)
    printer.output_dict({'header': 'Instance list (id, libvirt_name, name, status)'})
    status = dict({'total': 0})
    for i in instances:
        # Filter for project type
        if options.type:
            project = kc.get_by_id('project', i.tenant_id)
            if hasattr(project, 'type') and project.type != options.type:
                status['type'] = options.type
                continue
        output = {
             'id': i.id,
             'instance_name': getattr(i, 'OS-EXT-SRV-ATTR:instance_name'),
             'name': i.name,
             'status': i.status
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
    hosts = nc.get_hosts()
    printer.output_dict({'header': 'Hypervisor list (name, vms, state, status)'})
    for host in hosts:
        output = {
            'name': host.hypervisor_hostname,
            'state': host.state,
            'status': host.status,
            'running_vms': host.running_vms
        }
        printer.output_dict(output, sort=True, one_line=True)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
