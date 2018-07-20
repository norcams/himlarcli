#!/usr/bin/env python
""" Setup designate DNS """

import utils
from himlarcli.keystone import Keystone
from himlarcli.designate import Designate
from himlarcli import utils as himutils
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from collections import OrderedDict

himutils.is_virtual_env()

parser = Parser()
parser.set_autocomplete(True)
options = parser.parse_args()
printer = Printer(options.format)

kc= Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

dns = Designate(options.config, debug=options.debug)


if options.action[0] == 'show':
    if options.dry_run:
        print 'DRY-RUN: show'
    else:
        print 'show'
elif options.action[0] == 'create':
    if options.dry_run:
        print 'DRY-RUN: create'
    else:
        print 'create'

def action_list():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    blacklists = designateclient.list_blacklists()
    outputs = ['pattern','description','id']
    header = 'Blacklisted DNS domains (%s)' % (', '.join(outputs))
    printer.output_dict({'header': header})
    output = OrderedDict()
    if isinstance(blacklists, list):
        for b in blacklists:
            if not isinstance(b, dict):
                b = b.to_dict()
            for out in outputs:
                output[out] = b[out]
            printer.output_dict(objects=output, one_line=True, sort=False)

def action_create():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    designateclient.create_blacklist(pattern=options.pattern, description=options.comment)

def action_delete():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    designateclient.delete_blacklist(blacklist_id=options.blacklist_id)

def action_update():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    data = dict()
    if options.pattern:
        data['pattern'] = options.pattern
    if options.comment:
        data['description'] = options.comment
    designateclient.update_blacklist(blacklist_id=options.blacklist_id, values=data)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
