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

source = nc.get_fqdn(options.source)
search_opts = dict(all_tenants=1, host=source)

def action_list():
    instances = nc.get_all_instances(search_opts=search_opts)
    printer.output_dict({'header': 'Instance list (id, name, state)'})
    for i in instances:
        output = {
             'id': i.id,
             'name': i.name,
             'state': getattr(i, 'OS-EXT-STS:vm_state')
        }
        printer.output_dict(output, sort=True, one_line=True)

def action_migrate():
    target = nc.get_fqdn(options.target)
    dry_run_txt = 'DRY_RUN: ' if options.dry_run else ''
    instances = nc.get_all_instances(search_opts=search_opts)
    count = 0
    for i in instances:
        state = getattr(i, 'OS-EXT-STS:vm_state')
        logger.debug('=> %smigrate %s to %s', dry_run_txt, i.name, target)
        if state == 'active' and not options.dry_run:
            i.live_migrate(host=target)
            time.sleep(options.sleep)
        elif state == 'stopped' and not options.dry_run:
            i.migrate()
            time.sleep(options.sleep)
        else:
            logger.debug('=> dropping migrate of %s unknown state %s', i.name, state)
        count += 1
        if options.limit and count > options.limit:
            logger.debug('=> number of instances reached limit %s', options.limit)
            break

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
