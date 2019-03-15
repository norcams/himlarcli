#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
ksclient.set_domain(options.domain)
logger = ksclient.get_logger()

if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    himutils.sys_error('No valid regions found!')

def action_grant():
    # Get all users from a project
    users = ksclient.list_roles(project_name=options.project)
    for user in users:
        if user['role'] is not 'object':
            ksclient.grant_role(email=user['group'], project_name=options.project, role_name='object')

def action_revoke():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    # Get all users from a project
    users = ksclient.get_users(domain=options.domain, project=project.id)
    emails = list()
    for user in users:
        emails.append(user.email)
    ksclient.revoke_role(emails=emails, project_name=project.name, role_name='object')

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
