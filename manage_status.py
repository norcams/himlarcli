#!/usr/bin/env python
from himlarcli.parser import Parser
from himlarcli.status import Status
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
status = Status(options.config, debug=options.debug)
status.set_dry_run(options.dry_run)

def action_list():
    status.list(options.msg_type)

def action_delete():
    status_id = options.status_id
    if not himutils.confirm_action('Are you sure you want to delete status message with id %s' % status_id):
        return
    status.delete(status_id)

action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
