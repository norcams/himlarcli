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

source = nc.get_fqdn(options.source)
search_opts = dict(all_tenants=1, host=source)

if not nc.get_host(source):
    himutils.sys_error('Could not find source host %s' % source)

def action_list():
    instances = nc.get_all_instances(search_opts=search_opts)
    printer.output_dict({'header': 'Instance list (id, name, state, task)'})
    for i in instances:
        output = {
            'id': i.id,
            'name': i.name,
            'state': getattr(i, 'OS-EXT-STS:vm_state'),
            'state_task': getattr(i, 'OS-EXT-STS:task_state')
        }
        printer.output_dict(output, sort=True, one_line=True)

def action_migrate():
    target = nc.get_fqdn(options.target)
    if not nc.get_host(target):
        himutils.sys_error('Could not find target host %s' % target)
    q = 'Migrate all instances from %s to %s' % (source, target)
    if not himutils.confirm_action(q):
        return
    # Disable source host unless no-disable param is used
    if not options.dry_run and not options.no_disable:
        nc.disable_host(source)
    dry_run_txt = 'DRY_RUN: ' if options.dry_run else ''
    instances = nc.get_all_instances(search_opts=search_opts)
    count = 0
    for i in instances:
        state = getattr(i, 'OS-EXT-STS:vm_state')
        state_task = getattr(i, 'OS-EXT-STS:task_state')
        if state_task:
            logger.debug('=> instance running task %s, dropping migrate', state_task)
            continue
        logger.debug('=> %smigrate %s to %s', dry_run_txt, i.name, target)
        if (state == 'active' or state == 'paused') and not options.dry_run:
            i.live_migrate(host=target)
            time.sleep(options.sleep)
        # elif state == 'suspended' and not options.dry_run:
        #     i.resume()
        #     time.sleep(2)
        #     i.pause()
        #     time.sleep(5)
        #     i.live_migrate(host=target)
        #     time.sleep(options.sleep)
        elif not options.dry_run:
            logger.debug('=> dropping migrate of %s unknown state %s', i.name, state)
        count += 1
        if options.limit and count >= options.limit:
            logger.debug('=> number of instances reached limit %s', options.limit)
            break

def action_evacuate():
    source_host = nc.get_host(source)
    if source_host.state != 'down':
        himutils.sys_error('Evacuate failed. Source host need to be down! Use migrate')
    # Check that there are other valid hosts in the same aggregate
    hosts = nc.get_aggregate_hosts(options.aggregate)
    found_enabled = list()
    for host in hosts:
        if host.hypervisor_hostname == source:
            continue
        if host.status == 'enabled' and host.state == 'up':
            found_enabled.append(host.hypervisor_hostname)
    if not found_enabled:
        himutils.sys_error('Evacuate failed. No valid host in aggregate %s'
                           % options.aggregate)
    logger.debug('=> valid host found %s', ", ".join(found_enabled))
    # Interactive question
    q = 'Evacuate all instances from %s to other hosts' % source
    if not himutils.confirm_action(q):
        return
    instances = nc.get_all_instances(search_opts=search_opts)
    dry_run_txt = 'DRY_RUN: ' if options.dry_run else ''
    count = 0
    for i in instances:
        state = getattr(i, 'OS-EXT-STS:vm_state')
        logger.debug('=> %sevacuate %s', dry_run_txt, i.name)
        if state == 'active' and not options.dry_run:
            i.evacuate()
            time.sleep(options.sleep)
        elif state == 'stopped' and not options.dry_run:
            i.evacuate()
            time.sleep(options.sleep)
        elif not options.dry_run:
            logger.debug('=> dropping evacuate of %s unknown state %s', i.name, state)
        count += 1
        if options.limit and count > options.limit:
            logger.debug('=> number of instances reached limit %s', options.limit)
            break

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
