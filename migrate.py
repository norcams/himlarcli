#!/usr/bin/env python

import time

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.color import Color

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
    himutils.fatal(f"Could not find source host '{source}'")

def action_list():
    instances = nc.get_all_instances(search_opts=search_opts)

    if options.format == 'table':
        output = {}
        output['header'] = [
            'ID',
            'NAME',
            'VM_STATE',
            'TASK_STATE',
        ]
        output['align'] = [
            'l',
            'l',
            'l',
            'l',
        ]
        output['sortby'] = 2
        output['reversesort'] = True
        counter = 0

        for i in instances:
            state = getattr(i, 'OS-EXT-STS:vm_state')
            state_task = getattr(i, 'OS-EXT-STS:task_state')
            if state == 'active':
                state_color = Color.fg.GRN
            elif state == 'stopped':
                state_color = Color.fg.RED
            else:
                state_color = Color.fg.YLW
            if state_task is None:
                state_task_color = Color.dim
            else:
                state_task_color = Color.fg.red
            output[counter] = [
                Color.dim + i.id + Color.reset,
                Color.fg.ylw + i.name + Color.reset,
                state_color + str(getattr(i, 'OS-EXT-STS:vm_state')) + Color.reset,
                state_task_color + str(getattr(i, 'OS-EXT-STS:task_state')) + Color.reset,
            ]
            counter += 1
        printer.output_dict(output, sort=True, one_line=False)
    else:
        printer.output_dict({'header': 'Instance list (id, name, state, task)'})
        for i in instances:
            output = {
                'id':         i.id,
                'name':       i.name,
                'state':      getattr(i, 'OS-EXT-STS:vm_state'),
                'state_task': getattr(i, 'OS-EXT-STS:task_state'),
            }
            printer.output_dict(output, sort=True, one_line=True)

def action_migrate():
    target = nc.get_fqdn(options.target)
    target_details = nc.get_host(target)
    if not target_details or target_details.status != 'enabled':
        himutils.fatal(f'Could not find enabled target host {options.target}')
    if options.limit:
        q = f'Try to migrate {options.limit} instance(s) from {source} to {target}'
    else:
        q = f'Migrate ALL instances from {source} to {target}'
    if not himutils.confirm_action(q):
        return
    # Disable source host unless no-disable param is used
    if not options.dry_run and not options.no_disable:
        nc.disable_host(source)
    instances = nc.get_all_instances(search_opts=search_opts)
    count = 0
    for i in instances:
        if options.stopped and getattr(i, 'OS-EXT-STS:vm_state') != 'stopped':
            kc.debug_log(f'drop migrate:  instance not stopped {i.name}')
            continue # do not count this instance for limit
        if options.large:
            if i.flavor['ram'] > options.filter_ram:
                migrate_instance(i, target)
            else:
                kc.debug_log('drop migrate instance %s: ram %s <= %s'
                             % (i.name, i.flavor['ram'], options.filter_ram))
                continue # do not count this instance for limit
        elif options.small:
            if i.flavor['ram'] < options.filter_ram:
                migrate_instance(i, target)
            else:
                kc.debug_log('drop migrate instance %s: ram %s >= %s'
                             % (i.name, i.flavor['ram'], options.filter_ram))
                continue # do not count this instance for limit
        else:
            migrate_instance(i, target)
        count += 1
        if options.limit and count >= options.limit:
            kc.debug_log('number of instances reached limit %s' % options.limit)
            break

def action_evacuate():
    source_host = nc.get_host(source)
    if source_host.state != 'down':
        himutils.fatal('Evacuate failed. Source host need to be down! Use migrate')
    # Check that there are other valid hosts in the same aggregate
    hosts = nc.get_aggregate_hosts(options.aggregate)
    found_enabled = []
    for host in hosts:
        if host.hypervisor_hostname == source:
            continue
        if host.status == 'enabled' and host.state == 'up':
            found_enabled.append(host.hypervisor_hostname)
    if not found_enabled:
        himutils.sys_error(f'Evacuate failed. No valid host in aggregate {options.aggregate}')
    logger.debug('=> valid host found %s', ", ".join(found_enabled))
    # Interactive question
    q = f'Evacuate all instances from {source} to other hosts'
    if not himutils.confirm_action(q):
        return
    instances = nc.get_all_instances(search_opts=search_opts)
    dry_run_txt = 'DRY_RUN: ' if options.dry_run else ''
    count = 0
    for i in instances:
        state = getattr(i, 'OS-EXT-STS:vm_state')
        logger.debug(f'=> {dry_run_txt}evacuate {i.name}')
        if state == 'active' and not options.dry_run:
            i.evacuate()
            time.sleep(options.sleep)
        elif state == 'stopped' and not options.dry_run:
            i.evacuate()
            time.sleep(options.sleep)
        elif not options.dry_run:
            logger.debug(f'=> dropping evacuate of {i.name} unknown state {state}')
        count += 1
        if options.limit and count > options.limit:
            logger.debug(f'=> number of instances reached limit {options.limit}')
            break

def migrate_instance(instance, target):
    """
    This will do the migration of an instance to the target.
    Allowed state for migration:
        * active
        * paused
        * stopped
    """
    state = getattr(instance, 'OS-EXT-STS:vm_state')
    state_task = getattr(instance, 'OS-EXT-STS:task_state')
    # if there is any task running drop migrate
    if state_task:
        kc.debug_log('instance running task %s, dropping migrate' % state_task)
        himutils.warning(f'Instance {instance.name} ({instance.id} ' +
                         f'is running task {state_task}. Migration dropped')
        return
    kc.debug_log('migrate %s to %s' % (instance.name, target))
    if state == 'active':
        state_color = Color.fg.grn
    elif state == 'stopped':
        state_color = Color.fg.RED
    else:
        state_color = Color.fg.blu
    himutils.info(f'Migrating: {Color.fg.ylw}{instance.name}{Color.reset} '
                  f'({Color.dim}{instance.id}{Color.reset}) '
                  f'[{state_color}{state}{Color.reset}] ––→ {Color.fg.cyn}{target}{Color.reset}')
    if (state == 'active' or state == 'paused') and not options.dry_run:
        instance.live_migrate(host=target)
        time.sleep(options.sleep)
    elif state == 'stopped' and not options.dry_run:
        instance.migrate(host=target)
        time.sleep(options.sleep)
    elif not options.dry_run:
        kc.debug_log('dropping migrate of %s unknown state %s' % (instance.name, state))

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.fatal("Function action_%s() not implemented" % options.action)
action()
