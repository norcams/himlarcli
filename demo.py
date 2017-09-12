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
            printer.output_dict(output_project, sort=True, one_line=True)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
