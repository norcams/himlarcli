#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.neutron import Neutron
from himlarcli.glance import Glance
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli import utils as himutils
from datetime import datetime
from datetime import timedelta
from email.mime.text import MIMEText
from prettytable import PrettyTable
import re
import time

himutils.is_virtual_env()

parser = Parser()
parser.set_autocomplete(True)
options = parser.parse_args()
printer = Printer(options.format)
project_msg_file = 'notify/project_created.txt'
project_hpc_msg_file = 'notify/project_created_hpc.txt'
access_granted_msg_file = 'notify/access_granted_rt.txt'
access_granted_user_msg_file = 'notify/access_granted_user.txt'
access_revoked_msg_file = 'notify/access_revoked_rt.txt'
access_revoked_user_msg_file = 'notify/access_revoked_user.txt'
project_extended_msg_file = 'notify/project_extended.txt'

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
ksclient.set_domain(options.domain)
logger = ksclient.get_logger()
#novaclient = Nova(options.config, debug=options.debug, log=logger)

if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    himutils.sys_error('no regions found with this name!')

def action_create():
    if not ksclient.is_valid_user(options.admin, options.domain) and options.type == 'personal':
        himutils.sys_error('not valid user', 1)
    quota = himutils.load_config('config/quotas/%s.yaml' % options.quota)
    if options.quota and not quota:
        himutils.sys_error('Could not find quota in config/quotas/%s.yaml' % options.quota)
    test = 1 if options.type == 'test' else 0
    project_msg = project_msg_file

    today = datetime.today()
    if options.enddate == 'max':
        datetime_enddate = today + timedelta(days=730)
    elif re.match(r'^(\d\d\d\d-\d\d-\d\d)$', options.enddate):
        try:
            datetime_enddate = datetime.strptime(options.enddate, '%Y-%m-%d')
        except:
            himutils.sys_error('ERROR: Invalid date: %s' % options.enddate, 1)
    elif re.match(r'^(\d\d\.\d\d\.\d\d\d\d)$', options.enddate):
        try:
            datetime_enddate = datetime.strptime(options.enddate, '%d.%m.%Y')
        except:
            himutils.sys_error('ERROR: Invalid date: %s' % options.enddate, 1)
    else:
        himutils.sys_error('ERROR: Invalid date: %s' % options.enddate)
    enddate = datetime_enddate.strftime('%Y-%m-%d')

    if options.type == 'hpc':
        project_msg = project_hpc_msg_file
        if not enddate:
            himutils.sys_error('HPC projects must have an enddate', 1)
    createdate = datetime.today()

    # Parse the "contact" option, setting to None if not used
    # Exit with error if contact is not a valid email address
    contact = None
    if options.contact is not None:
        contact = options.contact.lower()
        if not ksclient._Keystone__validate_email(contact):
            errmsg = "%s is not a valid email address." % contact
            himutils.sys_error(errmsg, 1)

    if not options.force:
        print('Project name: %s\nDescription: %s\nAdmin: %s\nContact: %s\nOrganization: %s\nType: %s\nEnd date: %s\nQuota: %s\nRT: %s' \
                % (options.project,
                   options.desc,
                   options.admin.lower(),
                   contact,
                   options.org,
                   options.type,
                   str(enddate),
                   options.quota,
                   options.rt))
        if not himutils.confirm_action('Are you sure you want to create this project?'):
            himutils.sys_error('Aborted', 1)
    project = ksclient.create_project(project_name=options.project,
                                      admin=options.admin.lower(),
                                      contact=contact,
                                      org=options.org,
                                      test=test,
                                      type=options.type,
                                      description=options.desc,
                                      enddate=str(enddate),
                                      createdate=createdate.isoformat(),
                                      quota=options.quota,
                                      rt=options.rt)
    if not ksclient.is_valid_user(options.admin, options.domain):
        himutils.sys_error('WARNING: "%s" is not a valid user.' % options.admin, 0)
    if not project:
        himutils.sys_error('Failed creating %s' % options.project, 1)
    else:
        output = Keystone.get_dict(project)
        output['header'] = "Show information for %s" % options.project
        printer.output_dict(output)

    # Do stuff for regions
    for region in regions:
        # Get objects
        novaclient = himutils.get_client(Nova, options, logger, region)
        cinderclient = himutils.get_client(Cinder, options, logger, region)
        neutronclient = himutils.get_client(Neutron, options, logger, region)
        glanceclient = himutils.get_client(Glance, options, logger, region)

        # Find the project ID
        project_id = Keystone.get_attr(project, 'id')

        # Update quotas for Cinder, Nova, Neutron
        if quota and 'cinder' in quota and project:
            cinderclient.update_quota(project_id=project_id, updates=quota['cinder'])
        if quota and 'nova' in quota and project:
            novaclient.update_quota(project_id=project_id, updates=quota['nova'])
        if quota and 'neutron' in quota and project:
            neutronclient.update_quota(project_id=project_id, updates=quota['neutron'])

        # Grant UiO Managed images if shared UiO project
        if options.org == 'uio' and options.type not in [ 'personal', 'demo' ]:
            tags = [ 'uio' ]
            filters = {
                'status':     'active',
                'tag':        tags,
                'visibility': 'shared'
            }
            images = glanceclient.get_images(filters=filters)
            for image in images:
                glanceclient.set_image_access(image_id=image.id,
                                              project_id=project_id,
                                              action='grant')
                printer.output_msg('GRANT access to image {} for project {}'.
                               format(image.name, options.project))

    if options.mail:
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)

        if options.rt is None:
            himutils.sys_error('--rt parameter is missing.')
        else:
            mapping = dict(project_name=options.project,
                           admin=options.admin.lower(),
                           quota=options.quota,
                           end_date=str(enddate))
            subject = 'NREC: Project %s has been created' % options.project
            body_content = himutils.load_template(inputfile=project_msg,
                                                  mapping=mapping)
        if not body_content:
            himutils.sys_error('ERROR! Could not find and parse mail body in \
                               %s' % options.msg)

        mime = mail.rt_mail(options.rt, subject, body_content)
        mail.send_mail('support@nrec.no', mime)

def action_create_private():
    # Set default options
    options.type    = 'personal'
    options.project = 'PRIVATE-' + options.user.replace('@', '.').lower()
    options.admin   = options.user
    options.desc    = 'Personal project for %s' % options.user
    options.contact = None

    # Guess organization
    m = re.search(r'\@(.+?\.)?(?P<org>uio|uib|ntnu|nmbu|uit|vetinst|sikt)\.no', options.user)
    if m:
        options.org = m.group('org')
    else:
        himutils.sys_error('Can not guess organization. Run create manually', 1)

    # Set quota to small if not provided
    if not options.quota:
        options.quota = 'small'

    # Call main create function
    action_create()

def action_extend():
    project = ksclient.get_project_by_name(options.project)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)

    today = datetime.today()
    current = project.enddate if hasattr(project, 'enddate') else 'None'

    if options.enddate == 'max':
        datetime_enddate = today + timedelta(days=730)
    elif re.match(r'^\+(\d+)([y|m|d])$', options.enddate):
        if current == 'None':
            himutils.sys_error("Project does not have an existing enddate")
        else:
            datetime_current = datetime.strptime(project.enddate, '%Y-%m-%d')

        m = re.match(r'^\+(\d+)([y|m|d])$', options.enddate)
        if m.group(2) == 'y':
            datetime_enddate = datetime_current + timedelta(days=(365 * int(m.group(1))))
        elif m.group(2) == 'm':
            datetime_enddate = datetime_current + timedelta(days=(30 * int(m.group(1))))
        elif m.group(2) == 'd':
            datetime_enddate = datetime_current + timedelta(days=(int(m.group(1))))
    elif re.match(r'^(\d\d\d\d-\d\d-\d\d)$', options.enddate):
        try:
            datetime_enddate = datetime.strptime(options.enddate, '%Y-%m-%d')
        except:
            himutils.sys_error('ERROR: Invalid date: %s' % options.enddate, 1)
    elif re.match(r'^(\d\d\.\d\d\.\d\d\d\d)$', options.enddate):
        try:
            datetime_enddate = datetime.strptime(options.enddate, '%d.%m.%Y')
        except:
            himutils.sys_error('ERROR: Invalid date: %s' % options.enddate, 1)
    else:
        himutils.sys_error('ERROR: Invalid date: %s' % options.enddate, 1)

    enddate = datetime_enddate.strftime('%Y-%m-%d')
    ksclient.update_project(project_id=project.id, enddate=str(enddate),
                            disabled='', notified='', enabled=True)
    print("New end date for %s: %s" % (project.name, enddate))

    # Update RT
    if options.mail:
        project_msg = project_extended_msg_file
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)

        if options.rt is None:
            himutils.sys_error('--rt parameter is missing.')
        else:
            mapping = dict(project_name=project.name,
                           end_date=str(enddate))
            subject = 'NREC: New expiration date for project %s' % project.name
            body_content = himutils.load_template(inputfile=project_msg,
                                                  mapping=mapping)
        if not body_content:
            himutils.sys_error('ERROR! Could not find and parse mail body in \
                               %s' % options.msg)

        mime = mail.rt_mail(options.rt, subject, body_content)
        mail.send_mail('support@nrec.no', mime)


def action_grant():
    for user in options.users:
        if not ksclient.is_valid_user(email=user, domain=options.domain):
            himutils.sys_error('User %s not found as a valid user.' % user)
        project = ksclient.get_project_by_name(project_name=options.project)
        if not project:
            himutils.sys_error('No project found with name "%s"' % options.project)
        if hasattr(project, 'type') and (project.type == 'demo' or project.type == 'personal'):
            himutils.sys_error('Project are %s. User access not allowed!' % project.type)
        role = ksclient.grant_role(project_name=options.project,
                                   email=user)
        if role:
            output = role.to_dict() if not isinstance(role, dict) else role
            output['header'] = "Roles for %s" % options.project
            printer.output_dict(output)

    if options.mail:
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)

        if options.rt is None:
            himutils.sys_error('--rt parameter is missing.')
        else:
            rt_mapping = dict(users='\n'.join(options.users))
            rt_subject = 'NREC: Access granted to users in %s' % options.project
            rt_body_content = himutils.load_template(inputfile=access_granted_msg_file,
                                                     mapping=rt_mapping)

        rt_mime = mail.rt_mail(options.rt, rt_subject, rt_body_content)
        mail.send_mail('support@nrec.no', rt_mime)

        for user in options.users:
            mapping = dict(project_name=options.project, admin=project.admin)
            body_content = himutils.load_template(inputfile=access_granted_user_msg_file,
                                                  mapping=mapping)
            msg = MIMEText(body_content, 'plain')
            msg['subject'] = 'NREC: You have been given access to project %s' % options.project

            mail.send_mail(user, msg, fromaddr='noreply@nrec.no')

def action_revoke():
    for user in options.users:
        if not ksclient.is_valid_user(email=user, domain=options.domain):
            himutils.sys_error('User %s not found as a valid user.' % user)
        project = ksclient.get_project_by_name(project_name=options.project)
        if not project:
            himutils.sys_error('No project found with name "%s"' % options.project)
        role = ksclient.revoke_role(project_name=options.project,
                                    emails=[user])
        if role:
            output = role.to_dict() if not isinstance(role, dict) else role
            output['header'] = "Roles for %s" % options.project
            printer.output_dict(output)

    if options.mail:
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)

        if options.rt is None:
            himutils.sys_error('--rt parameter is missing.')
        else:
            rt_mapping = dict(users='\n'.join(options.users))
            rt_subject = 'NREC: Access revoked for users in %s' % options.project
            rt_body_content = himutils.load_template(inputfile=access_revoked_msg_file,
                                                     mapping=rt_mapping)

        rt_mime = mail.rt_mail(options.rt, rt_subject, rt_body_content)
        mail.send_mail('support@nrec.no', rt_mime)

        for user in options.users:
            mapping = dict(project_name=options.project, admin=project.admin)
            body_content = himutils.load_template(inputfile=access_revoked_user_msg_file,
                                                  mapping=mapping)
            msg = MIMEText(body_content, 'plain')
            msg['subject'] = 'NREC: Your access to project %s is revoked' % options.project

            mail.send_mail(user, msg, fromaddr='noreply@nrec.no')

def action_delete():
    question = 'Delete project %s and all resources' % options.project
    if not options.force and not himutils.confirm_action(question):
        return

    # Delete the project
    ksclient.delete_project(options.project)
    printer.output_msg('DELETED project: {}'. format(options.project))

def action_list():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(**search_filter)
    count = 0
    if options.quarantined:
        printer.output_dict({'header': 'Quarantined project list (Q-date, Q-reason, admin, enddate, id, name)'})
    else:
        printer.output_dict({'header': 'Project list (admin, enddate, id, name, org, type)'})
    for project in projects:
        project_type = project.type if hasattr(project, 'type') else 'None'
        project_admin = project.admin if hasattr(project, 'admin') else 'None'
        project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
        project_org = project.org if hasattr(project, 'org') else 'None'

        # If we want to list by org or project type
        if options.list_org != 'all' and options.list_org != project_org:
            continue
        if options.list_type != 'all' and options.list_type != project_type:
            continue

        # If we want to list quarantined projects
        if options.quarantined:
            if not ksclient.check_project_tag(project.id, 'quarantine_active'):
                continue
            tags = ksclient.list_project_tags(project.id)
            r_date = re.compile('^quarantine date: .+$')
            r_type = re.compile('^quarantine type: .+$')
            date_tags = list(filter(r_date.match, tags))
            type_tags = list(filter(r_type.match, tags))
            if len(date_tags) > 1:
                himutils.sys_error('Too many quarantine dates for project %s' % project.name)
                continue
            elif len(date_tags) < 1:
                himutils.sys_error('No quarantine date for project %s' % project.name)
                continue
            if len(type_tags) > 1:
                himutils.sys_error('Too many quarantine reasons for project %s' % project.name)
                continue
            elif len(type_tags) < 1:
                himutils.sys_error('No quarantine reason for project %s' % project.name)
                continue
            m_date = re.match(r'^quarantine date: (\d\d\d\d-\d\d-\d\d)$', date_tags[0])
            m_type = re.match(r'^quarantine type: (.+)$', type_tags[0])
            quarantine_date_iso = m_date.group(1)
            quarantine_reason = m_type.group(1)

            if options.quarantined_reason != 'all' and options.quarantined_reason != quarantine_reason:
                continue

            if options.quarantined_before or options.quarantined_after:
                quarantine_date = time.strptime(quarantine_date_iso, "%Y-%m-%d")
                if options.quarantined_before:
                    before_date = time.strptime(options.quarantined_before, "%Y-%m-%d")
                    if quarantine_date > before_date:
                        continue
                elif options.quarantined_after:
                    after_date = time.strptime(options.quarantined_after, "%Y-%m-%d")
                    if quarantine_date < after_date:
                        continue

        # Slightly different output if we are listing quarantined projects
        if options.quarantined:
            output_project = {
                'id': project.id,
                'name': project.name,
                'admin': project_admin,
                'enddate': project_enddate,
                'Q-date:': quarantine_date_iso,
                'Q-reason': quarantine_reason,
            }
        else:
            output_project = {
                'id': project.id,
                'name': project.name,
                'type': project_type,
                'org': project_org,
                'admin': project_admin,
                'enddate': project_enddate,
            }

        count += 1
        printer.output_dict(output_project, sort=True, one_line=True)
    printer.output_dict({'header': 'Project list count', 'count': count})

def action_show_access():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    roles = ksclient.list_roles(project_name=options.project)
    printer.output_dict({'header': 'Roles in project %s' % options.project})
    for role in roles:
        printer.output_dict(role, sort=True, one_line=True)

def action_show_quota():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.sys_error('could not find project {}'.format(options.project))
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        components = {'nova': novaclient, 'cinder': cinderclient, 'neutron': neutronclient}
        for comp, client in components.items():
            if options.service != 'all' and comp != options.service:
                continue
            quota = dict()
            if hasattr(client, 'get_quota'):
                quota = getattr(client, 'get_quota')(project.id)
            else:
                logger.debug('=> function get_quota_class not found for %s' % comp)
                continue
            if quota:
                quota.update({'header': '%s quota in %s' % (comp, region), 'region': region})
                #printer.output_dict({'header': 'Roles in project %s' % options.project})
                printer.output_dict(quota)

def action_show():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    output_project = project.to_dict()
    output_project['header'] = "Show information for %s" % project.name
    printer.output_dict(output_project)

def action_instances():
    project = ksclient.get_project_by_name(project_name=options.project)
    for region in regions:
        novaclient = himutils.get_client(Nova, options, logger, region)
        instances = novaclient.get_project_instances(project_id=project.id)
        if not instances:
            ksclient.debug_log('No instances found for the project {} in {}'.
                               format(options.project, region))
            continue
        printer.output_dict({'header': 'Instances list (id, name, region)'})
        count = 0
        for i in instances:
            output = {
                'id': i.id,
                'name': i.name,
                'region': region,
            }
            count += 1
            printer.output_dict(output, sort=True, one_line=True)
        printer.output_dict({'header': 'Total instances in this project', 'count': count})

def action_quarantine():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)

    # Add or remove quarantine
    if options.unset_quarantine:
        ksclient.project_quarantine_unset(options.project)
        printer.output_msg('Quarantine unset for project: {}'. format(options.project))
    else:
        if not options.reason:
            himutils.sys_error("Option '--reason' is required")
            return

        if options.date:
            date = himutils.get_date(options.date, None, '%Y-%m-%d')
        else:
            date = datetime.now().strftime("%Y-%m-%d")

        if options.mail and options.reason == 'enddate':
            project_contact = project.contact if hasattr(project, 'contact') else 'None'
            project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
            project_admin = project.admin if hasattr(project, 'admin') else 'None'

            if not options.template:
                himutils.sys_error("Option '--template' is required when sending mail")
                return

            # Set common mail parameters
            mail = himutils.get_client(Mail, options, logger)
            mail = Mail(options.config, debug=options.debug)
            mail.set_dry_run(options.dry_run)
            fromaddr = 'support@nrec.no'
            bccaddr = 'iaas-logs@usit.uio.no'
            if project_contact != 'None':
                ccaddr = project_contact
            else:
                ccaddr = None

            options.detail = True # we want details
            options.admin = project_admin  # for prettyprint_project_metadata()

            attachment_payload = ''
            attachment_payload += Printer.prettyprint_project_metadata(project, options, logger, regions, project_admin)
            attachment_payload += Printer.prettyprint_project_zones(project, options, logger)
            attachment_payload += Printer.prettyprint_project_volumes(project, options, logger, regions)
            attachment_payload += Printer.prettyprint_project_images(project, options, logger, regions)
            attachment_payload += Printer.prettyprint_project_instances(project, options, logger, regions)

            # Construct mail content
            subject = 'NREC: Project "%s" is scheduled for deletion' % project.name
            body_content = himutils.load_template(inputfile=options.template,
                                                  mapping={'project': project.name,
                                                           'enddate': project_enddate},
                                                  log=logger)
            msg = mail.create_mail_with_txt_attachment(subject,
                                                       body_content,
                                                       attachment_payload,
                                                       'resources.txt',
                                                       fromaddr,
                                                       ccaddr)
            # Send mail to user
            mail.send_mail(project_admin, msg, fromaddr, ccaddr, bccaddr)
            if options.dry_run:
                print("Did NOT send spam to %s;" % project_admin)
                print("Subject: %s" % subject)
                print("To: %s" % project_admin)
                if ccaddr:
                    print("Cc: %s" % ccaddr)
                if bccaddr:
                    print("Bcc: %s" % bccaddr)
                print("From: %s" % fromaddr)
                print('---')
                print(body_content)
            else:
                print("Spam sent to %s" % project_admin)

        ksclient.project_quarantine_set(options.project, options.reason, date)
        printer.output_msg('Quarantine set for project: {}'. format(options.project))

def action_access():
    #------------------------------+-----------------------------------+---------+
    #       Text color             |       Background color            |         |
    #--------------+---------------+----------------+------------------+         |
    # Base color   |Lighter shade  |  Base color    | Lighter shade    |         |
    #--------------+---------------+----------------+------------------+         |
    BLK='\033[30m'; blk='\033[90m'; BBLK='\033[40m'; bblk='\033[100m' #| Black   |
    RED='\033[31m'; red='\033[91m'; BRED='\033[41m'; bred='\033[101m' #| Red     |
    GRN='\033[32m'; grn='\033[92m'; BGRN='\033[42m'; bgrn='\033[102m' #| Green   |
    YLW='\033[33m'; ylw='\033[93m'; BYLW='\033[43m'; bylw='\033[103m' #| Yellow  |
    BLU='\033[34m'; blu='\033[94m'; BBLU='\033[44m'; bblu='\033[104m' #| Blue    |
    MGN='\033[35m'; mgn='\033[95m'; BMGN='\033[45m'; bmgn='\033[105m' #| Magenta |
    CYN='\033[36m'; cyn='\033[96m'; BCYN='\033[46m'; bcyn='\033[106m' #| Cyan    |
    WHT='\033[37m'; wht='\033[97m'; BWHT='\033[47m'; bwht='\033[107m' #| White   |
    #------------------------------------------------------------------+---------+
    # Effects                                                                    |
    #----------------------------------------------------------------------------+
    DEF='\033[0m'   #Default color and effects                                   |
    BLD='\033[1m'   #Bold\brighter                                               |
    DIM='\033[2m'   #Dim\darker                                                  |
    CUR='\033[3m'   #Italic font                                                 |
    UND='\033[4m'   #Underline                                                   |
    INV='\033[7m'   #Inverted                                                    |
    COF='\033[?25l' #Cursor Off                                                  |
    CON='\033[?25h' #Cursor On                                                   |
    #----------------------------------------------------------------------------+

    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.fatal('No project found with name %s' % options.project)

    # Correct use of options
    if options.grant and options.revoke:
        himutils.fatal("Can't use both --grant and --revoke")
    elif not options.grant and not options.revoke and not options.access_extend and not options.access_list:
        himutils.fatal("Either --grant or --revoke is mandatory")

    # Resource availability by region
    resource_availability = {
        'vgpu'       : [ 'bgo', 'osl' ],
        'shpc'       : [ 'bgo', 'osl' ],
        'shpc_ram'   : [ 'bgo' ],
        'shpc_disk1' : [ 'osl' ],
        'shpc_disk2' : [ 'osl' ],
        'shpc_disk3' : [ 'osl' ],
        'shpc_disk4' : [ 'osl' ],
        'ssd'        : [ 'bgo', 'osl' ],
        'net_uib'    : [ 'bgo' ],
    }

    # Today
    today = datetime.now().strftime("%Y-%m-%d")

    # Determine resource end date when granting access
    if options.grant or options.access_extend:
        if not options.until:
            resource_enddate = 'None'
        elif options.until == 'None':
            resource_enddate = 'None'
        else:
            if re.match(r'^(\d\d\d\d-\d\d-\d\d)$', options.until):
                try:
                    datetime_until = datetime.strptime(options.until, '%Y-%m-%d')
                except:
                    himutils.fatal('Invalid date: %s' % options.until)
            elif re.match(r'^(\d\d\.\d\d\.\d\d\d\d)$', options.until):
                try:
                    datetime_until = datetime.strptime(options.until, '%d.%m.%Y')
                except:
                    himutils.fatal('Invalid date: %s' % options.until)
            else:
                himutils.fatal('Invalid date: %s' % options.until)

            # check that resource enddate doesn't exceed project enddate
            if hasattr(project, 'enddate'):
                datetime_project_end = datetime.strptime(project.enddate, '%Y-%m-%d')
                datetime_today = datetime.strptime(today, '%Y-%m-%d')
                if datetime_until > datetime_project_end:
                    himutils.fatal('Resource enddate %s exceeds project enddate %s'
                                   % (datetime_until.strftime('%Y-%m-%d'), project.enddate))
                elif datetime_until <= datetime_today:
                    himutils.fatal('Resource enddate %s is in the past'
                                   % datetime_until.strftime('%Y-%m-%d'))

            # If we've come this far we have a valid resource enddate
            resource_enddate = datetime_until.strftime('%Y-%m-%d')

    # Determine access action, type of resource and add or delete tags
    if options.grant:
        access_action = 'grant'
        resource = options.grant
        if not any(x in regions for x in resource_availability[resource]):
            himutils.fatal('Resource %s is not available in any of the regions %s'
                           % (resource, regions))
        # Set tags
        if ksclient.check_project_tag(project.id, '%s_access' % resource):
            himutils.warning('Tag "%s_access" already exists for %s'
                             % (resource, project.name))
        else:
            ksclient.add_project_tag(project.id, '%s_access' % resource)
            himutils.info('Added project tag: %s_access' % resource)
            ksclient.add_project_tag(project.id, '%s_start: %s' % (resource, today))
            himutils.info('Added project tag: %s_start: %s' % (resource, today))
            ksclient.add_project_tag(project.id, '%s_end: %s' % (resource, resource_enddate))
            himutils.info('Added project tag: %s_end: %s' % (resource, resource_enddate))
        for region in regions:
            if region not in resource_availability[resource]:
                himutils.warning('Resource %s is not available in region %s, skipping...'
                                 % (resource, region))
                continue
            if ksclient.check_project_tag(project.id, '%s_region_%s' % (resource, region)):
                himutils.warning('Tag "%s_region_%s" already exists for %s'
                                 % (resource, region, project.name))
            else:
                ksclient.add_project_tag(project.id, '%s_region_%s' % (resource, region))
                himutils.info('Added project tag: %s_region_%s' % (resource, region))
    elif options.revoke:
        access_action = 'revoke'
        resource = options.revoke
        for region in regions:
            if ksclient.check_project_tag(project.id, '%s_region_%s' % (resource, region)):
                ksclient.delete_project_tag(project.id, '%s_region_%s' % (resource, region))
                himutils.info('Deleted project tag: %s_region_%s' % (resource, region))
            else:
                himutils.warning('Tag "%s_region_%s" does not exist for %s'
                                 % (resource, region, project.name))
        tags = ksclient.list_project_tags(project.id)
        delete_tags = True
        for tag in tags:
            if re.match(r'^%s_region_.+$' % resource, tag):
                delete_tags = False
        # Remove tags
        if delete_tags:
            r = re.compile(r'^%s_(access|(start|end): .+)$' % resource)
            for tag in list(filter(r.match, tags)):
                ksclient.delete_project_tag(project.id, tag)
                himutils.info('Deleted project tag: %s' % tag)
    elif options.access_extend:
        resource = options.access_extend
        tags = ksclient.list_project_tags(project.id)
        r = re.compile('^%s_end: .*' % resource)
        for tag in list(filter(r.match, tags)):
            ksclient.delete_project_tag(project.id, tag)
            himutils.info('Deleted project tag: %s' % tag)
        ksclient.add_project_tag(project.id, '%s_end: %s' % (resource, resource_enddate))
        himutils.info('Added project tag: %s_end: %s' % (resource, resource_enddate))
        return
    elif options.access_list:
        tags = ksclient.list_project_tags(project.id)
        rdict = dict()
        for tag in tags:
            m = re.match(r'^(.+?)_access$', tag)
            if m:
                rdict[m.group(1)] = ['unknown','unknown']
        for tag in tags:
            for r in rdict.keys():
                mstart = re.match(r'^%s_start: (.+)$' % r, tag)
                mend   = re.match(r'^%s_end: (.+)$' % r, tag)
                if mstart:
                    rdict[r][0] = mstart.group(1)
                if mend:
                    rdict[r][1] = mend.group(1)
        # print info about resources and return
        print('%sPROJECT: %s%s' % (blu, project.name, DEF))
        header = [ '%sRESOURCE%s' % (UND,DEF),
                   '%sSTART DATE%s' % (UND,DEF),
                   '%sEND DATE%s' % (UND,DEF)]
        for region in regions:
            header.append('%s%s%s' % (UND,region.upper(),DEF))
        table_resource = PrettyTable()
        table_resource._max_width = {'value' : 70}
        table_resource.border = 0
        table_resource.header = 1
        table_resource.left_padding_width = 2
        table_resource.field_names = header
        table_resource.align[header[0]] = 'l'
        table_resource.align[header[1]] = 'l'
        table_resource.align[header[2]] = 'l'
        for r in rdict.keys():
            row = [ r, rdict[r][0], rdict[r][1] ]
            for region in regions:
                if ksclient.check_project_tag(project.id, '%s_region_%s' % (r, region)):
                    row.append('%s\u2713%s' % (grn,DEF))
                else:
                    row.append('%s-%s' % (red,DEF))
            table_resource.add_row(row)
        table_resource.sortby = header[0]
        print(table_resource)
        return

    # If option is given to only handle tags, return here
    if options.tags_only:
        return

    # Determine flavors and shared images
    access_flavors = list()
    access_images = list()
    access_volumetype = list()
    access_networks = list()
    if resource == 'vgpu':
        access_flavors.append('vgpu.m1')
        access_images.append('vgpu')
    elif resource == 'shpc':
        access_flavors.append('shpc.m1a')
        access_flavors.append('shpc.c1a')
    elif resource == 'shpc_ram':
        access_flavors.append('shpc.r1a')
    elif resource == 'shpc_disk1':
        access_flavors.append('shpc.m1ad1')
        access_flavors.append('shpc.c1ad1')
    elif resource == 'shpc_disk2':
        access_flavors.append('shpc.m1ad2')
        access_flavors.append('shpc.c1ad2')
    elif resource == 'shpc_disk3':
        access_flavors.append('shpc.m1ad3')
        access_flavors.append('shpc.c1ad3')
    elif resource == 'shpc_disk4':
        access_flavors.append('shpc.m1ad4')
        access_flavors.append('shpc.c1ad4')
    elif resource == 'ssd':
        access_volumetype.append('mass-storage-ssd')
    elif resource == 'net_uib':
        access_networks.append('uib-dualStack')

    # Loop through regions and grant/revoke access
    for region in regions:

        # Skip region if resource not available in this region
        if region not in resource_availability[resource]:
            continue

        # Grant/Revoke access to flavors
        for flavor in access_flavors:
            # First look for region version of flavor config, then the default one
            if himutils.file_exists('config/flavors/%s-%s.yaml' % (flavor, region)):
                configfile = 'config/flavors/%s-%s.yaml' % (flavor, region)
            else:
                configfile = 'config/flavors/%s.yaml' % (flavor)

            flavors = himutils.load_config(configfile)
            if not flavors:
                himutils.fatal('Could not find flavor config file config/flavors/%s.yaml' % flavor)

            if flavors[flavor]:
                novaclient = himutils.get_client(Nova, options, logger, region)
                result = novaclient.update_flavor_access(class_filter=flavor,
                                                         project_id=project.id,
                                                         action=access_action)
                if result:
                    himutils.info('%s flavor access to %s for %s in %s'
                                  % (access_action.upper(), flavor, options.project, region))
                else:
                    himutils.error('Failed to %s flavor access to %s for %s in %s'
                                   % (access_action.upper(), flavor, options.project, region))

        # Grant/Revoke access to shared images
        if access_images:
            glanceclient = himutils.get_client(Glance, options, logger, region)
            filters = {
                'status':     'active',
                'tag':        access_images,
                'visibility': 'shared'
            }
            images = glanceclient.get_images(filters=filters)
            for image in images:
                result = glanceclient.set_image_access(image_id=image.id,
                                                       project_id=project.id,
                                                       action=access_action)
                if result:
                    himutils.info('%s access to image %s for project %s in %s'
                                  % (access_action.upper(), image.name, options.project, region))
                else:
                    himutils.error('Failed to %s access to image %s for project %s in %s'
                                   % (access_action.upper(), image.name, options.project, region))

        # Grant/Revoke access to volume types
        for volume_type_name in access_volumetype:
            cinderclient = himutils.get_client(Cinder, options, logger, region)
            nonpublic_volume_types = cinderclient.get_nonpublic_volume_types()
            for vtype in nonpublic_volume_types:
                if vtype.name == volume_type_name:
                    break

            result = cinderclient.update_volume_type_access(access_action, project.id, vtype)
            if result:
                himutils.info("%s volume type access to %s for %s in %s"
                              % (access_action.upper(), volume_type_name, options.project, region))
            else:
                himutils.error("Failed to %s volume type access to %s for %s in %s"
                               % (access_action.upper(), volume_type_name, options.project, region))

        # Grant/Revoke access to networks
        for network_name in access_networks:
            neutronclient = himutils.get_client(Neutron, options, logger, region)
            net = neutronclient.get_network_by_name(network_name)

            result = neutronclient.update_network_access(access_action, project.id, net['id'])
            if result:
                himutils.info("%s network access to %s for %s in %s"
                              % (access_action.upper(), network_name, options.project, region))
            else:
                himutils.error("Failed to %s network access to %s for %s in %s"
                               % (access_action.upper(), network_name, options.project, region))


def action_access_list():
    #------------------------------+-----------------------------------+---------+
    #       Text color             |       Background color            |         |
    #--------------+---------------+----------------+------------------+         |
    # Base color   |Lighter shade  |  Base color    | Lighter shade    |         |
    #--------------+---------------+----------------+------------------+         |
    BLK='\033[30m'; blk='\033[90m'; BBLK='\033[40m'; bblk='\033[100m' #| Black   |
    RED='\033[31m'; red='\033[91m'; BRED='\033[41m'; bred='\033[101m' #| Red     |
    GRN='\033[32m'; grn='\033[92m'; BGRN='\033[42m'; bgrn='\033[102m' #| Green   |
    YLW='\033[33m'; ylw='\033[93m'; BYLW='\033[43m'; bylw='\033[103m' #| Yellow  |
    BLU='\033[34m'; blu='\033[94m'; BBLU='\033[44m'; bblu='\033[104m' #| Blue    |
    MGN='\033[35m'; mgn='\033[95m'; BMGN='\033[45m'; bmgn='\033[105m' #| Magenta |
    CYN='\033[36m'; cyn='\033[96m'; BCYN='\033[46m'; bcyn='\033[106m' #| Cyan    |
    WHT='\033[37m'; wht='\033[97m'; BWHT='\033[47m'; bwht='\033[107m' #| White   |
    #------------------------------------------------------------------+---------+
    # Effects                                                                    |
    #----------------------------------------------------------------------------+
    DEF='\033[0m'   #Default color and effects                                   |
    BLD='\033[1m'   #Bold\brighter                                               |
    DIM='\033[2m'   #Dim\darker                                                  |
    CUR='\033[3m'   #Italic font                                                 |
    UND='\033[4m'   #Underline                                                   |
    INV='\033[7m'   #Inverted                                                    |
    COF='\033[?25l' #Cursor Off                                                  |
    CON='\033[?25h' #Cursor On                                                   |
    #----------------------------------------------------------------------------+

    resource = options.resource

    # Search for projects
    search_filter = {}
    search_filter['tags_any'] = ['%s_access' % resource]
    projects = ksclient.get_projects(**search_filter)

    print('%sRESOURCE: %s%s' % (mgn, resource, DEF))
    header = [ '%sPROJECT%s' % (UND,DEF),
               '%sSTART DATE%s' % (UND,DEF),
               '%sEND DATE%s' % (UND,DEF)]
    for region in regions:
        header.append('%s%s%s' % (UND,region.upper(),DEF))
    table_resource = PrettyTable()
    table_resource._max_width = {'value' : 70}
    table_resource.border = 0
    table_resource.header = 1
    table_resource.left_padding_width = 2
    table_resource.field_names = header
    table_resource.align[header[0]] = 'l'
    table_resource.align[header[1]] = 'l'
    table_resource.align[header[2]] = 'l'

    for project in projects:
        tags = ksclient.list_project_tags(project.id)
        for tag in tags:
            mstart = re.match(r'^%s_start: (.+)$' % resource, tag)
            mend   = re.match(r'^%s_end: (.+)$' % resource, tag)
            if mstart:
                start = mstart.group(1)
            if mend:
                end = mend.group(1)

        row = [ project.name, start, end ]
        for region in regions:
            if ksclient.check_project_tag(project.id, '%s_region_%s' % (resource, region)):
                row.append('%s\u2713%s' % (grn,DEF))
            else:
                row.append('%s-%s' % (red,DEF))
        table_resource.add_row(row)

    table_resource.sortby = header[0]
    print(table_resource)


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
