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

if 'host' in options and options.host:
    if '.' in options.host:
        host = options.host
    else:
        domain = ksclient.get_config('openstack', 'domain')
        host = options.host + '.' + domain
else:
    host = None

# Send mail to all emails in a template file
def action_file():
    user_counter = 0
    sent_mail_counter = 0
    if options.template:
        content = options.template
        email_content = open(content, 'r')
        body_content = email_content.read()
        if options.dry_run:
            print body_content
        else:
            mail = Mail(options.config, debug=options.debug)
            msg = MIMEText(body_content)
            msg['subject'] = subject
            print msg
            with open(emails_file, 'r') as emails:
                for toaddr in emails.readlines():
                    user_counter += 1
                    try:
                        logger.debug('=> Sending email ...')
                        mail.send_mail(toaddr, msg, fromaddr='noreply@uh-iaas.no')
                        sent_mail_counter += 1
                    except ValueError:
                        himutils.sys_error('Not able to send the email.')
            emails.close()
            print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
    email_content.close()
    mail.close()

# Send mail to all running instances
def action_instance():
    user_counter = 0
    sent_mail_counter = 0
    if options.template:
        content = options.template
        email_content = open(content, 'r')
        body_content = email_content.read()
        if options.dry_run:
            print body_content
        else:
            with open(content, 'r') as email_content:
                body_content = email_content.read()
            for region in regions:
                novaclient = himutils.get_client(Nova, options, logger, region)
                instances = novaclient.get_instances()
                user_counter += 1
                mail = Mail(options.config, debug=options.debug)
                try:
                    logger.debug('=> Sending email ...')
                    mail.set_keystone_client(ksclient)
                    users = mail.mail_instance_owner(instances=instances,
                                                       body=body_content,
                                                       subject=subject,
                                                       admin=True)
                    sent_mail_counter += 1
                except ValueError:
                        himutils.sys_error('Not able to send the email.')
            print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
    mail.close()

# Send mail to a specific type of project
def action_project():
    user_counter = 0
    sent_mail_counter = 0
    mail = Mail(options.config, debug=options.debug)
    search_filter = dict()
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    if options.template:
        content = options.template
        email_content = open(content, 'r')
        body_content = email_content.read()
        if options.dry_run:
            print body_content
        else:
            with open(content, 'r') as email_content:
                body_content = email_content.read()
            if options.filter and options.filter != 'all':
                search_filter['type'] = options.filter
            if options.type:
                search_filter['type'] = options.type
            for region in regions:
                for project in projects:
                    project_type = project.type if hasattr(project, 'type') else '(unknown)'
                    novaclient = himutils.get_client(Nova, options, logger, region)
                    instances = novaclient.get_project_instances(project.id)
                    user_counter += 1
                    try:
                        logger.debug('=> Sending email ...')
                        mail.set_keystone_client(ksclient)
                        users = mail.mail_instance_owner(instances=instances,
                                                           body=body_content,
                                                           subject=subject,
                                                           admin=True)
                        sent_mail_counter += 1
                    except ValueError:
                        himutils.sys_error('Not able to send the email.')
            print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
    mail.close()

# Send mail to all the users
def action_sendtoall():
    user_counter = 0
    sent_mail_counter = 0
    users = ksclient.get_users(domain=options.domain)
    projects = ksclient.list_projects('Dataporten')
    mail = Mail(options.config, debug=options.debug)
    if options.template:
        content = options.template
        email_content = open(content, 'r')
        body_content = email_content.read()
        if options.dry_run:
            print body_content
        else:
            with open(content, 'r') as email_content:
                body_content = email_content.read()
            for user in users:
                for project in projects:
                    mail = Mail(options.config, debug=options.debug)
                    msg = MIMEText(body_content)
                    msg['subject'] = subject
                    toaddr = user.email
                    user_counter += 1
                    if hasattr(user, 'email'):
                        try:
                            logger.debug('=> Sending email ...')
                            mail.send_mail(toaddr, msg, fromaddr='noreply@uh-iaas.no')
                            sent_mail_counter += 1
                        except ValueError:
                            himutils.sys_error('Not able to send the email.')
            print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
    mail.close()

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
