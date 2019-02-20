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

emails_file = 'notify/user_emails.txt'
body_content = 'notify/mailto_all.txt'
subject = 'test123'


if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    himutils.sys_error('no valid regions found!')

def action_file():
    mail = Mail(options.config, debug=options.debug)
    with open(emails_file, 'r') as file:
        for line in file:
            toadr = file.readline() #mail_to_adr
            mail.send_mail('support@uh-iaas.no', body_content, subject, toadr)
            
    #if --dry-run, only print the content
    if options.dry_run:
        email_content = open(body_content, 'r')
        print('\n' + email_content.read() + '\n')

    # ToDo
    # if -t use template, otherwise use default

def action_instance():
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        mapping = dict(region=region.upper())
        body_content = himutils.load_template(inputfile=options.template,
                                                mapping=mapping,
                                                log=logger)
        subject = options.subject
        mail.set_keystone_client(ksclient)
        mail.set_dry_run(options.dry_run)
    
        users = mail.mail_instance_owner(instances, body_content, subject)
        print(users)

        # users = mail.mail_instance_owner(instances=instances,
        #                                     body=body_content,
        #                                     subject=subject,
        #                                     admin=True,
        #                                     options=['project', 'az'])

def action_project():
    mail = Mail(options.config, debug=options.debug)
    if options.type:
        search_filter['type'] = options.type
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    for project in projects:
        if not options.filter or options.filter in project.name:
            instances = novaclient.get_project_instances(project.id)
            mapping = dict(region=region.upper(), project=project.name)
            body_content = himutils.load_template(inputfile=options.template,
                                                  mapping=mapping,
                                                  log=logger)
            subject = ('UH-IaaS: Your instances will be terminated (%s)' % (region))

            mail.set_keystone_client(ksclient)
            mail.set_dry_run(options.dry_run)
            users = mail.mail_instance_owner(instances, body_content, subject)
            print users

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
