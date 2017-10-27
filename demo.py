#!/usr/bin/env python
import time
from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.notify import Notify
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()


def action_create():
    users = ksclient.get_users(domain=options.domain)
    printer.output_dict({'header': 'Created demo project'})
    count = 0
    for user in users:
        if not hasattr(user, 'email'):
            logger.debug('=> %s user missing email' % user.name)
            continue
        search_filter = dict({'type': 'demo'})
        projects = ksclient.get_user_projects(email=user.email.lower(),
                                              domain=options.domain,
                                              **search_filter)
        if projects:
            logger.debug('=> user %s has demo project' % user.email.lower())
        else:
            logger.debug('=> create demo project for user %s' % user.email.lower())
            project_name = user.email.lower().replace('@', '.')
            project_name = 'DEMO-%s' % project_name
            desc = ('Personal demo project for %s. Resources might be '
                    'terminated at any time.' % user.email.lower())
            ksclient.create_project(domain=options.domain,
                                    project_name=project_name,
                                    description=desc,
                                    type='demo',
                                    admin=user.email.lower())
            output_user = {
                'id': user.id,
                'name': user.name,
            }
            count += 1
            printer.output_dict(output_user, sort=True, one_line=True)
    printer.output_dict({'Users without demo project': count})

def action_notify():
    question = 'Send mail to all users about demo projects'
    if options.dry_run:
        question = 'DRY-RUN: %s' % question
    if not himutils.confirm_action(question):
        return

    projects = ksclient.get_projects(domain=options.domain)
    count = 0
    for project in projects:
        if hasattr(project, 'notify') and project.notify == 'converted':
            himutils.sys_error('personal project %s converted' % (project.name), 0)
            continue
        found = False
        if hasattr(project, 'type') and project.type == 'personal':
            print "%s (new personal project)" % project.name
            count += 1
            found = True
        elif '@' in project.name and not hasattr(project, 'type'):
            print "%s (old personal project)" % project.name
            count += 1
            found = True
        if found:
            if '@' not in project.name:
                himutils.sys_error('unable to find email for project %s' % project.name, 0)
                continue
            user = ksclient.get_user_by_email(project.name, 'api', options.domain)
            if not user:
                himutils.sys_error('unable to find user for project %s' % project.name, 0)
                continue
            search_filter = dict({'type': 'demo'})
            demo_project = ksclient.get_user_projects(email=user.email.lower(),
                                                      domain=options.domain,
                                                      **search_filter)
            demo_project = demo_project[0] if demo_project else None
            if not demo_project:
                himutils.sys_error('unable to find demo project for %s' % user.name, 0)
                continue
            delete_date = '2017-10-31'

            sent_email = himutils.load_file('temp_email.txt', log=ksclient.get_logger())
            if user.email in sent_email:
                imutils.sys_error('%s email sent, dropping' % user.email)
                continue
            #ksclient.update_project(project_id=project.id, notify=delete_date)
            #mapping = dict(region=region.upper(), project=project.name)
            mapping = {'personal': project.name, 'date': delete_date, 'demo': demo_project.name}
            body_content = himutils.load_template(inputfile='misc/notify_demo2.txt',
                                                  mapping=mapping,
                                                  log=logger)
            subject = ('[UH-IaaS] Your personal project will be deleted')
            notify = Notify(options.config, debug=False, log=logger)
            notify.set_dry_run(options.dry_run)
            notify.mail_user(body_content, subject, user.email)
            notify.close()
            time.sleep(3)
    printer.output_dict({'Personal projects': count})

def action_validate():
    valid_projects = ['personal', 'demo', 'research', 'education', 'admin', 'test']
    projects = ksclient.get_projects(domain=options.domain)
    # validate all projects
    printer.output_dict({'header': 'Projects with failed validation'})
    count = 0
    for project in projects:
        output_project = dict()
        if not hasattr(project, 'type'):
            output_project = {
                'id': project.id,
                'name': project.name,
                'reason': '(missing project type)'
            }
        elif project.type == 'personal' and '@' in project.name:
            output_project = {
                'id': project.id,
                'name': project.name,
                'reason': '(old personal project)'
            }
        elif project.type not in valid_projects:
            output_project = {
                'id': project.id,
                'name': project.name,
                'reason': '(%s not valid type)' % project.type
            }
        if output_project:
            count += 1
            printer.output_dict(output_project, sort=True, one_line=True)
    printer.output_dict({'Projects with failed validation': count})
    users = ksclient.get_users(domain=options.domain)
    printer.output_dict({'header': 'Users without demo project'})
    count = 0
    for user in users:
        if not hasattr(user, 'email'):
            logger.debug('=> %s user missing email' % user.name)
            continue
        search_filter = dict({'type': 'demo'})
        projects = ksclient.get_user_projects(email=user.email,
                                              domain=options.domain,
                                              **search_filter)

        demo_project = False
        for project in projects:
            if hasattr(project, 'type') and project.type == 'demo':
                # user has demo project continue with next user
                demo_project = True
                break
        if not demo_project:
            output_user = {
                'id': user.id,
                'name': user.name,
                'reason': '(missing demo project)'
            }
            count += 1
            printer.output_dict(output_user, sort=True, one_line=True)
    printer.output_dict({'Users without demo project': count})

def action_convert():
    project = ksclient.get_project_by_name(options.project, options.domain)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    if not hasattr(project, 'notify'):
        himutils.sys_error('Project not old personal project %s (missing notify)'
                           % options.project)
    desc = 'Personal project for %s' % options.project
    admin = options.project
    notify = 'converted'
    project_type = 'personal'
    test = 0
    project_name = options.project.lower().replace('@', '.')
    project_name = 'PRIVATE-%s' % project_name

    ksclient.update_project(project_id=project.id,
                            project_name=project_name,
                            description=desc,
                            type=project_type,
                            notify=notify,
                            admin=admin,
                            test=test)
    printer.output_dict({'Converted project': options.project})

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
