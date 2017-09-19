#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=logger)

def action_create():
#    TODO: implement quota
#    quota = himutils.load_config('config/quotas/%s.yaml' % options.quota)
#    if options.quota and not quota:
#        himutils.sys_error('Could not find quota in config/quotas/%s.yaml' % options.quota)
    test = 1 if options.type == 'test' else 0
    project = ksclient.create_project(domain=options.domain,
                                      project=options.project,
                                      admin=options.admin.lower(),
                                      test=test,
                                      type=options.type,
                                      description=options.desc,
                                      quota={})
    if project:
        output = project.to_dict() if not isinstance(project, dict) else project
        output['header'] = "Show information for %s" % options.project
        printer.output_dict(output)
    if project and ksclient.is_valid_user(email=options.admin, domain=options.domain):
        role = ksclient.grant_role(project_name=options.project,
                                   email=options.admin,
                                   domain=options.domain)
        if role:
            output = role.to_dict() if not isinstance(role, dict) else role
            output['header'] = "Roles for %s" % options.project
            printer.output_dict(output)
    elif project:
        himutils.sys_error("admin %s not found as a user. no access granted!" % options.admin, 0)

def action_grant():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        himutils.sys_error('User %s not found as a valid user.' % options.user)
    project = ksclient.get_project_by_name(project_name=options.project, domain=options.domain)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    if hasattr(project, 'type') and (project.type == 'demo' or project.type == 'personal'):
        himutils.sys_error('Project are %s. User access not allowed!' % project.type)
    role = ksclient.grant_role(project_name=options.project,
                               email=options.user,
                               domain=options.domain)
    if role:
        output = role.to_dict() if not isinstance(role, dict) else role
        output['header'] = "Roles for %s" % options.project
        printer.output_dict(output)

def action_delete():
    question = 'Delete project %s and all resources' % options.project
    if not options.force and not himutils.confirm_action(question):
        return
    ksclient.delete_project(options.project, domain=options.domain)

def action_list():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
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

def action_show():
    project = ksclient.get_project_by_name(project_name=options.project, domain=options.domain)
    if not project:
        himutils.sys_error('No project found with name %s' % options.project)
    output_project = project.to_dict()
    output_project['header'] = "Show information for %s" % project.name
    printer.output_dict(output_project)
    roles = ksclient.list_roles(project_name=options.project)
    printer.output_dict({'header': 'Roles in project %s' % options.project})
    for role in roles:
        printer.output_dict(role, sort=True, one_line=True)

#         project = ksclient.get_project(project=options.project, domain=domain)
#         pp = pprint.PrettyPrinter(indent=1)
#         pp.pprint(project.to_dict())
#     else:
#         print 'project name must be set to show project'




# # Input args
# desc = 'Perform action on shared project (not course and personal)'
# actions = ['list', 'show', 'create', 'grant', 'delete', 'quota']
# opt_args = { '-p': { 'dest': 'project', 'help': 'project name', 'metavar': 'name'},
#              '-u': { 'dest': 'user', 'help': 'email of user', 'metavar': 'user'},
#              '-q': { 'dest': 'quota', 'help': 'project quota', 'default': 'default', 'metavar': 'quota'},
#              '-t': { 'dest': 'type', 'help': 'project type (default admin)', 'default': 'admin', 'metavar': 'type'}}
# options = utils.get_action_options(desc, actions, opt_args=opt_args, dry_run=True)
# ksclient = Keystone(options.config, debug=options.debug)
# novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
# quota = himutils.load_config('config/quota.yaml')
# project_types = himutils.load_config('config/type.yaml', log=ksclient.get_logger())
# domain='Dataporten'
#
# if options.action[0] == 'create':
#     if options.quota not in quota:
#         print 'ERROR! Quota %s unknown. Check valid quota in config/quota.yaml' % options.quota
#         sys.exit(1)
#     if options.type not in project_types['types']:
#         print 'ERROR! Type %s is not valid. Check valid types in config/type.yaml' % options.type
#         sys.exit(1)
#     if options.project and options.user:
#         if not ksclient.is_valid_user(email=options.user, domain=domain):
#             print "ERROR! %s is not a valid user. Group from access not found!" % options.user
#             sys.exit(1)
#         if options.type == 'test':
#             test = 1
#         else:
#             test = 0
#         if not options.dry_run:
#             project = ksclient.create_project(domain=domain,
#                                               project=options.project,
#                                               admin=options.user.lower(),
#                                               test=test,
#                                               type=options.type,
#                                               quota=quota[options.quota])
#             pp = pprint.PrettyPrinter(indent=1)
#             if project:
#                 pp.pprint(project.to_dict())
#                 ksclient.grant_role(project=options.project,
#                                     user=options.user,
#                                     role='user',
#                                     domain=domain)
#         else:
#             print 'Run in dry-run mode. No project created'
#     else:
#         print 'ERROR! user and project name must be set to create project'
#         sys.exit(1)
# if options.action[0] == 'grant':
#     if options.project and options.user:
#         ksclient.grant_role(project=options.project,
#                                     user=options.user,
#                                     role='user',
#                                     domain=domain)
#     else:
#         print 'user and project name must be set to grant project access'
# if options.action[0] == 'delete':
#     if options.project:
#         q = "Delete project and all instances for %s (yes|no)? " % options.project
#         answer = raw_input(q)
#         if answer.lower() == 'yes':
#             print "We are now deleting project and instances for %s" % options.project
#             print 'Please wait...'
#             ksclient.delete_project(options.project, domain=domain)
#         else:
#             print "You just dodged a bullet my friend!"
#     else:
#         print 'project name must be set to delete project'
# if options.action[0] == 'quota':
#     if options.project:
#         quota = ksclient.list_quota(project=options.project, domain=domain)
#         pp = pprint.PrettyPrinter(indent=1)
#         if 'compute' in quota:
#             pp.pprint(quota['compute'].to_dict())
#     else:
#         print 'project name must be set to show quota'

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
