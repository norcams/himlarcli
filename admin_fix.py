#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

regions = kc.find_regions()

def action_list():
    projects = kc.get_projects(type='demo')
    for project in projects:
        if not hasattr(project, 'admin'):
            roles = kc.list_roles(project_name=project.name)
            if len(roles) > 0:
                admin = roles[0]['group'].split('-')[0].lower()
                print "{} => {}".format(project.name, admin)
                kc.update_project(project.id, admin=admin)

def action_update():
    projects = kc.get_projects(type='demo')
    for project in projects:
        if not hasattr(project, 'admin'):
            roles = kc.list_roles(project_name=project.name)
            if len(roles) > 0:
                admin = roles[0]['group'].split('-group')[0].lower()
                print "{} => {}".format(project.name, admin)
                kc.update_project(project.id, admin=admin)

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
