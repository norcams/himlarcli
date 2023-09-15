#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

import re

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
    # Get project, make sure it is valid
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.fatal(f'Project not found: {options.project}')

    # Get all users from project
    users = ksclient.list_roles(project_name=options.project)

    # Grant object role for all users
    for user in users:
        rc = ksclient.grant_role(email=user['group'], project_name=options.project, role_name='object')
        if rc == ksclient.ReturnCode.OK:
            himutils.info(f"Granted object access in {options.project} to {user.group}")
        elif rc == ksclient.ReturnCode.ALREADY_MEMBER:
            himutils.warning(f"User {user.group} already has object access in {options.project}")

def action_revoke():
    # Get project, make sure it is valid
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.fatal(f'Project not found: {options.project}')

    # Get all users from project
    #users = ksclient.get_users(domain=options.domain, project=project.id)
    users = ksclient.list_roles(project_name=options.project)

    # Revoke object role for all users
    for user in users:
        if user['role'] == 'object':
            email = re.sub('(-group|-disabled)$', '', user['group'])
            rc = ksclient.revoke_role(email=email, project_name=options.project, role_name='object')
            if rc == ksclient.ReturnCode.OK:
                himutils.info(f"Revoked object access in {options.project} from {email}")
            elif rc == ksclient.ReturnCode.NOT_MEMBER:
                himutils.warning(f"User {email} does not have object access in {options.project}")

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
