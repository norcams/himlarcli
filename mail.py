#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
#from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
from himlarcli.mail import Mail

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()
#
# if not regions:
#     himutils.sys_error('no valid regions found!')
#
# if 'host' in options and options.host:
#     if '.' in options.host:
#         host = options.host
#     else:
#         domain = ksclient.get_config('openstack', 'domain')
#         host = options.host + '.' + domain
# else:
#     host = None


# Send mail template to all emails in a address file
def action_file():
    q = 'Send mail template {} to all emails in {}'.format(options.template,
                                                           options.email_file)
    if not utils.confirm_action(q):
        return
    sent_mail_counter = 0
    mail = Mail(options.config, debug=options.debug)
    mail.set_dry_run(options.dry_run)
    body_content = utils.load_template(inputfile=options.template, mapping={}, log=logger)
    emails = utils.load_file(inputfile=options.email_file, log=logger)
    for email in emails:
        mail.mail_user(body_content, options.subject, email)
        sent_mail_counter += 1
    mail.close()
    printer.output_dict({'header': 'Mail counter', 'count': sent_mail_counter})

def action_aggregate():
    users = dict()
    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        #neutron = utils.get_client(Neutron, options, logger)
        #network = neutron.list_networks()
        instances = nova.get_instances(options.aggregate)
        if not instances:
            continue
        for i in instances:
            email = None
            project = kc.get_by_id('project', i.tenant_id)
            if hasattr(project, 'admin'):
                email = project.admin
            else:
                kc.debug_log('could not find admin for project {}'.
                             format(project.name))
                continue
            instance_data = {
                'name': i.name,
                'region': region,
                #'status': i.status,
                #'created': i.created,
                #'flavor': i.flavor['original_name'],
                #'ip': next(iter(neutron.get_network_ip(i.addresses, network)), None),
                'project': project.name

            }
            if email not in users:
                users[email] = list()
            users[email].append(instance_data)

        # Add metadata to aggregate
        if options.date:
            meta_msg = options.date + ' (updated {})'.format(utils.get_current_date())
        else:
            meta_msg = 'unknown (updated {})'.format(utils.get_current_date())
        metadata = {'maintenance': meta_msg}
        nova.update_aggregate(options.aggregate, metadata=metadata)

    mailer = utils.get_client(Mail, options, logger)
    if '[NREC]' not in options.subject:
        subject = '[NREC] ' + options.subject
    else:
        subject = options.subject
    sent_mail_counter = 0
    message = None
    fromaddr = options.from_addr
    for user, instances in users.iteritems():
        columns = ['project', 'region']
        mapping = dict(region=options.region,
                       date=options.date,
                       instances=utils.get_instance_table(instances, columns),
                       admin=user)
        body_content = utils.load_template(inputfile=options.template,
                                           mapping=mapping,
                                           log=logger)
        message = mailer.get_mime_text(subject, body_content, fromaddr=fromaddr)
        mailer.send_mail(user, message)
        sent_mail_counter += 1

    if options.dry_run and message:
        print "\nExample mail sendt from this run:"
        print "----------------------------------"
        print message
    mailer.close()
    printer.output_dict({'header': 'Mail counter', 'count': sent_mail_counter})

# Send mail to all running instances
# def action_instance():
#     user_counter = 0
#     sent_mail_counter = 0
#     if options.template:
#         content = options.template
#         email_content = open(content, 'r')
#         body_content = email_content.read()
#         if options.dry_run:
#             print body_content
#         else:
#             with open(content, 'r') as email_content:
#                 body_content = email_content.read()
#             for region in regions:
#                 novaclient = himutils.get_client(Nova, options, logger, region)
#                 instances = novaclient.get_instances()
#                 user_counter += 1
#                 mail = Mail(options.config, debug=options.debug)
#                 try:
#                     logger.debug('=> Sending email ...')
#                     mail.set_keystone_client(ksclient)
#                     users = mail.mail_instance_owner(instances=instances,
#                                                      body=body_content,
#                                                      subject=subject,
#                                                      admin=True)
#                     sent_mail_counter += 1
#                 except ValueError:
#                         himutils.sys_error('Not able to send the email.')
#             print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
#     mail.close()

# Send mail to a specific type of project
# def action_project():
#     himutils.sys_error('FIXME: this is not working')
#     user_counter = 0
#     sent_mail_counter = 0
#     mail = Mail(options.config, debug=options.debug)
#     search_filter = dict()
#     projects = ksclient.get_projects(**search_filter)
#     if options.template:
#         content = options.template
#         email_content = open(content, 'r')
#         body_content = email_content.read()
#         if options.dry_run:
#             print body_content
#         else:
#             with open(content, 'r') as email_content:
#                 body_content = email_content.read()
#             if options.filter and options.filter != 'all':
#                 search_filter['type'] = options.filter
#             if options.type:
#                 search_filter['type'] = options.type
#             for region in regions:
#                 for project in projects:
#                     project_type = project.type if hasattr(project, 'type') else '(unknown)'
#                     novaclient = himutils.get_client(Nova, options, logger, region)
#                     instances = novaclient.get_project_instances(project.id)
#                     user_counter += 1
#                     try:
#                         logger.debug('=> Sending email ...')
#                         mail.set_keystone_client(ksclient)
#                         users = mail.mail_instance_owner(instances=instances,
#                                                            body=body_content,
#                                                            subject=subject,
#                                                            admin=True)
#                         sent_mail_counter += 1
#                     except ValueError:
#                         himutils.sys_error('Not able to send the email.')
#             print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
#     mail.close()

# Send mail to all the users
# def action_sendtoall():
#     logfile = 'logs/mail-sendtoall-{}.log'.format(date.today().isoformat())
#     user_counter = 0
#     sent_mail_counter = 0
#     users = ksclient.get_users(domain=options.domain, enabled=True)
#     mail = Mail(options.config, debug=False, log=logger)
#     mail.set_dry_run(options.dry_run)
#     if options.template:
#         content = options.template
#         email_content = open(content, 'r')
#         body_content = email_content.read()
#         # if options.dry_run:
#         #     print body_content
#         # else:
#         with open(content, 'r') as email_content:
#             body_content = email_content.read()
#         for user in users:
#             msg = MIMEText(body_content)
#             msg['subject'] = options.subject
#             toaddr = user.email
#             user_counter += 1
#             if hasattr(user, 'email') and '@' in user.email:
#                 try:
#                     mail.send_mail(toaddr, msg, fromaddr='noreply@uh-iaas.no')
#                     sent_mail_counter += 1
#                     time.sleep(2)
#                 except ValueError:
#                     himutils.sys_error('Not able to send the email.')
#             if not options.dry_run:
#                 himutils.append_to_file(logfile, toaddr)
#         print '\nSent %s mail(s) to %s user(s)' % (sent_mail_counter, user_counter)
#     mail.close()

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
