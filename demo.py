#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()

def action_validate():
    valid_projects = ['demo', 'research', 'education', 'admin', 'test']
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
        obj = ksclient.get_user_objects(email=user.email, domain=options.domain)
        demo_project = False
        for project in obj['projects']:
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

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
