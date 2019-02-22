#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.mail import Mail
from email.mime.text import MIMEText


himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()

# Update these before running the script
emails_file = 'notify/user_emails.txt'
content = 'notify/mailto_all.txt'
subject = 'INFO UH-IaaS'


if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    himutils.sys_error('no valid regions found!')

def action_file():
    if options.template:
        content = options.template
        email_content = open(content, 'r')
        body_content = email_content.read()
        if options.dry_run:
            print content
            #logger.debug('=> DRY-RUN: print out the content %s' % content)
        else:
            print "jooooo"
            mail = Mail(options.config, debug=options.debug)
            mail.set_dry_run(options.dry_run)
            msg = MIMEText(body_content, 'plain')
            msg['subject'] = subject
            print msg
            with open(emails_file, 'r') as emails:
                for toaddr in emails.readlines():
                    try:
                        logger.debug('=> Sending email ...')
                        #print msg
                        mail.send_mail(toaddr, msg, fromaddr='noreply@usit.uio.no')
                    except ValueError:
                        himutils.sys_error('Not able to send the email.')
            emails.close()
    email_content.close()

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
