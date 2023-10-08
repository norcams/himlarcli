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
    himutils.fatal('No valid regions found!')

def action_grant():
    # Get project, make sure it is valid
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.fatal(f'Project not found: {options.project}')

    # Get all users from project
    project_users = ksclient.list_roles(project_name=options.project)

    # If option '-u' is specified, limit to the specified
    # users. Otherwise grant access to all project users
    if options.users:
        users = [x for x in project_users if x['group'].replace('-group', '') in options.users]
    else:
        users = project_users

    # Grant object role for all users
    for user in users:
        if user['role'] != 'user':
            continue
        rc = ksclient.grant_role(email=user['group'], project_name=options.project, role_name='object')
        this_user = user['group'].replace('-group','')
        if rc == ksclient.ReturnCode.OK:
            himutils.info(f"Granted object access in {options.project} for {this_user}")
        elif rc == ksclient.ReturnCode.ALREADY_MEMBER:
            himutils.warning(f"User {this_user} already has object access in {options.project}")

def action_revoke():
    # Get project, make sure it is valid
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.fatal(f'Project not found: {options.project}')

    # Get all users from project
    project_users = ksclient.list_roles(project_name=options.project)

    # If option '-u' is specified, limit to the specified
    # users. Otherwise revoke access to all project users
    if options.users:
        users = [x for x in project_users if x['group'].replace('-group', '') in options.users]
    else:
        users = project_users

    # Revoke object role for all users
    for user in users:
        if user['role'] == 'object':
            email = re.sub('(-group|-disabled)$', '', user['group'])
            rc = ksclient.revoke_role(email=email, project_name=options.project, role_name='object')
            if rc == ksclient.ReturnCode.OK:
                himutils.info(f"Revoked object access in {options.project} for {email}")

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.fatal(f"Function action_{options.action}() not implemented")
action()
