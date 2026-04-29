#!/usr/bin/env python
import sys
import os
from jinja2 import Environment, meta
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.slack2 import Slack
from himlarcli.status import Status
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

slack = Slack(options.config, debug=options.debug)
status = Status(options.config, debug=options.debug)

def confirm_publish(final_msg):
    lines = final_msg.splitlines()
    width = max((len(l) for l in lines), default=0)
    border = '─' * (width + 2)
    print('┌' + border + '┐')
    for line in lines:
        print('│ ' + line.ljust(width) + ' │')
    print('└' + border + '┘')
    if not himutils.confirm_action('Are you sure you want to publish?'):
        sys.exit(1)

def parse_template():
    template_path = himutils.get_abs_path(options.template)
    if not os.path.isfile(template_path):
        himutils.sys_error("Template not found: %s" % template_path)
    with open(template_path, 'r') as f:
        content = f.read()
    if '{{' in content:
        return _render_jinja_template(content)
    else:
        return _render_legacy_template(content)

def _render_jinja_template(content):
    env = Environment()
    variables = sorted(meta.find_undeclared_variables(env.parse(content)))
    mapping = {}
    print("Fill in template variables (press Enter to leave blank):")
    for var in variables:
        value = input("  %s: " % var)
        mapping[var] = value
    return env.from_string(content).render(**mapping).rstrip('\n')

def _render_legacy_template(content):
    mapping = {}
    if options.region:
        mapping['region'] = options.region.upper()
    if options.date:
        mapping['date'] = options.date
    msg_content = himutils.load_template(inputfile=options.template,
                                         mapping=mapping)
    return msg_content.rstrip('\n')

def action_important():
    important_msg = msg
    if options.link:
        important_msg += " For live updates visit https://status.uh-iaas.no"
    confirm_publish(important_msg)
    slack.publish_slack(important_msg)
    status.publish(important_msg, msg_type='important')

def action_news():
    confirm_publish(msg)
    slack.publish_slack(msg)
#    status.publish(msg)

def action_info():
    confirm_publish(msg)
    status.publish(msg)

def action_event():
    confirm_publish(msg)
    status.publish(msg, msg_type='event')

if options.message:
    msg = options.message
elif options.template:
    msg = parse_template()
else:
    himutils.sys_error("No template or message given.")

slack.set_dry_run(options.dry_run)
status.set_dry_run(options.dry_run)
# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
