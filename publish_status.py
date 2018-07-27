#!/usr/bin/env python
import time
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.slack import Slack
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

def action_slack():
    msg_content = himutils.load_template(inputfile=options.template,
                                         mapping={})
    stripped_msg = msg_content.rstrip('\n')
    slack = Slack(options.config, debug=options.debug)
    slack.set_dry_run(options.dry_run)
    slack.publish_slack(stripped_msg)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
