#!/usr/bin/env python
import time
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.slack import Slack
from himlarcli.twitter import Twitter
from himlarcli.status import Status
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

slack = Slack(options.config, debug=options.debug)
twitter = Twitter(options.config, debug=options.debug)
status = Status(options.config, debug=options.debug)

def action_important():
    important_msg = msg
    if options.link:
        important_msg += " For live updates visit https://status.uh-iaas.no"
    if not himutils.twitter_length(important_msg):
        himutils.sys_error("Message cannot contain more than 280 characters")
    print('The following message will be published: %s' % important_msg)
    if not himutils.confirm_action('Are you sure you want to publish?'):
        return
    slack.publish_slack(important_msg)
    twitter.publish_twitter(important_msg)
    status.publish_status(important_msg, msg_type='important')

def action_info():
    if not himutils.twitter_length(msg):
        himutils.sys_error("Message cannot contain more than 280 characters")
    print('The following message will be published: %s' % msg)
    if not himutils.confirm_action('Are you sure you want to publish?'):
        return
    twitter.publish_twitter(msg)
    status.publish_status(msg)

def parse_template():
    mapping = {}
    if options.region:
        mapping['region'] = options.region.upper()
    if options.date:
        mapping['date'] = options.date
    msg_content = himutils.load_template(inputfile=options.template,
                                         mapping=mapping)
    stripped_msg = msg_content.rstrip('\n')
    return stripped_msg

if options.message:
    msg = options.message
elif options.template:
    msg = parse_template()
else:
    himutils.sys_error("No template or message given.")

slack.set_dry_run(options.dry_run)
twitter.set_dry_run(options.dry_run)
status.set_dry_run(options.dry_run)
# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
