#!/usr/bin/env python
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

def confirm_publish(final_msg):
    print('The following message will be published: %s' % final_msg)
    if not himutils.confirm_action('Are you sure you want to publish?'):
        return

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

def action_important():
    important_msg = msg
    if options.link:
        important_msg += " For live updates visit https://status.uh-iaas.no"
    confirm_publish(important_msg)
    if not twitter.twitter_length(important_msg):
        himutils.sys_error("Message cannot contain more than 280 characters")
    slack.publish_slack(important_msg)
    twitter.publish_twitter(important_msg)
    status.publish(important_msg, msg_type='important')

def action_info():
    if not twitter.twitter_length(msg):
        himutils.sys_error("Message cannot contain more than 280 characters")
    confirm_publish(msg)
    twitter.publish_twitter(msg)
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
twitter.set_dry_run(options.dry_run)
status.set_dry_run(options.dry_run)
# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
