#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli import utils as himutils
from datetime import datetime
from email.mime.text import MIMEText
import re

himutils.is_virtual_env()

parser = Parser()
parser.set_autocomplete(True)
options = parser.parse_args()
printer = Printer(options.format)
project_msg_file = 'notify/project_created.txt'
project_hpc_msg_file = 'notify/project_created_hpc.txt'
access_msg_file = 'notify/access_granted_rt.txt'
access_user_msg_file = 'notify/access_granted_user.txt'

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
    enddate = himutils.get_date(options.enddate, None, '%d.%m.%Y')
    if options.type == 'hpc':
        project_msg = project_hpc_msg_file
        if not enddate:
            himutils.sys_error('HPC projects must have an enddate', 1)
    createdate = datetime.today()
    if not options.force:
        print 'Project name: %s\nDescription: %s\nAdmin: %s\nType: %s\nEnd date: %s\nQuota: %s\nRT: %s' \
                % (options.project,
                   ksclient.convert_ascii(options.desc),
                   options.admin.lower(),
                   options.type,
                   str(enddate),
                   options.quota,
                   options.rt)
        if not himutils.confirm_action('Are you sure you want to create this project?'):
            himutils.sys_error('Aborted', 1)
    project = ksclient.create_project(project_name=options.project,
                                      admin=options.admin.lower(),
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

    # Quotas
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        cinderclient.set_dry_run(options.dry_run)
        novaclient.set_dry_run(options.dry_run)
        neutronclient.set_dry_run(options.dry_run)
        project_id = Keystone.get_attr(project, 'id')
        if quota and 'cinder' in quota and project:
            cinderclient.update_quota(project_id=project_id, updates=quota['cinder'])
        if quota and 'nova' in quota and project:
            novaclient.update_quota(project_id=project_id, updates=quota['nova'])
        if quota and 'neutron' in quota and project:
            neutronclient.update_quota(project_id=project_id, updates=quota['neutron'])

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
            subject = 'UH-IaaS: Project %s has been created' % options.project
            body_content = himutils.load_template(inputfile=project_msg,
                                                  mapping=mapping)
        if not body_content:
            himutils.sys_error('ERROR! Could not find and parse mail body in \
                               %s' % options.msg)

        mime = mail.rt_mail(options.rt, subject, body_content)
        mail.send_mail('support@uh-iaas.no', mime)

def action_extend():
    project = ksclient.get_project_by_name(options.project)
    if not project:
        msg = 'Could not find any project named {}'.format(options.project)
        himutils.sys_error(msg)

    enddate = himutils.get_date(options.enddate, None, '%d.%m.%Y')
    ksclient.update_project(project_id=project.id, enddate=str(enddate),
                            disabled='', notified='', enabled=True)

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
            rt_subject = 'UH-IaaS: Access granted to users in %s' % options.project
            rt_body_content = himutils.load_template(inputfile=access_msg_file,
                                                     mapping=rt_mapping)

        rt_mime = mail.rt_mail(options.rt, rt_subject, rt_body_content)
        mail.send_mail('support@uh-iaas.no', rt_mime)

        for user in options.users:
            mapping = dict(project_name=options.project, admin=project.admin)
            body_content = himutils.load_template(inputfile=access_user_msg_file,
                                                  mapping=mapping)
            msg = MIMEText(body_content, 'plain')
            msg['subject'] = 'UH-IaaS: You have been given access to project %s' % options.project

            mail.send_mail(user, msg, fromaddr='no-reply@uh-iaas.no')

def action_delete():
    question = 'Delete project %s and all resources' % options.project
    if not options.force and not himutils.confirm_action(question):
        return
    ksclient.delete_project(options.project)

def action_list():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(**search_filter)
    count = 0
    printer.output_dict({'header': 'Project list (id, name, type)'})
    for project in projects:
        project_type = project.type if hasattr(project, 'type') else '(unknown)'
        output_project = {
            'id': project.id,
            'name': project.name,
            'type': project_type,
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
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        cinderclient = Cinder(options.config, debug=options.debug, log=logger, region=region)
        neutronclient = Neutron(options.config, debug=options.debug, log=logger, region=region)
        components = {'nova': novaclient, 'cinder': cinderclient, 'neutron': neutronclient}
        for comp, client in components.iteritems():
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

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
