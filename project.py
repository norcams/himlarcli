#!/usr/bin/python
import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils

# Input args
desc = 'Perform project action'
actions = ['list', 'show', 'create', 'grant', 'delete', 'quota']
opt_args = { '-p': { 'dest': 'project', 'help': 'project name', 'metavar': 'name'},
             '-u': { 'dest': 'user', 'help': 'email of user', 'metavar': 'user'},
             '-q': { 'dest': 'quota', 'help': 'project quota', 'default': 'default', 'metavar': 'quota'},
             '-t': { 'dest': 'type', 'help': 'project type (default admin)', 'default': 'admin', 'metavar': 'type'}}
options = utils.get_action_options(desc, actions, opt_args=opt_args, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
quota = himutils.load_config('config/quota.yaml')
project_types = himutils.load_config('config/type.yaml', log=ksclient.get_logger())
domain='Dataporten'

if options.action[0] == 'create':
    if options.quota not in quota:
        print 'ERROR! Quota %s unknown. Check valid quota in config/quota.yaml' % options.quota
        sys.exit(1)
    if options.type not in project_types['types']:
        print 'ERROR! Type %s is not valid. Check valid types in config/type.yaml' % options.type
        sys.exit(1)
    if options.project and options.user:
        if not ksclient.is_valid_user(user=options.user, domain=domain):
            print "ERROR! %s is not a valid user. Group from access not found!" % options.user
            sys.exit(1)
        if options.type == 'test':
            test = 1
        else:
            test = 0
        if not options.dry_run:
            project = ksclient.create_project(domain=domain,
                                              project=options.project,
                                              admin=options.user,
                                              test=test,
                                              type=options.type,
                                              quota=quota[options.quota])
            pp = pprint.PrettyPrinter(indent=1)
            if project:
                pp.pprint(project.to_dict())
                ksclient.grant_role(project=options.project,
                                    user=options.user,
                                    role='user',
                                    domain=domain)
        else:
            print 'Run in dry-run mode. No project created'
    else:
        print 'ERROR! user and project name must be set to create project'
        sys.exit(1)
if options.action[0] == 'grant':
    if options.project and options.user:
        ksclient.grant_role(project=options.project,
                                    user=options.user,
                                    role='user',
                                    domain=domain)
    else:
        print 'user and project name must be set to grant project access'
if options.action[0] == 'delete':
    if options.project:
        q = "Delete project and all instances for %s (yes|no)? " % options.project
        answer = raw_input(q)
        if answer.lower() == 'yes':
            print "We are now deleting project and instances for %s" % options.project
            print 'Please wait...'
            ksclient.delete_project(options.project, domain=domain)
        else:
            print "You just dodged a bullet my friend!"
    else:
        print 'project name must be set to delete project'
if options.action[0] == 'list':
    projects = ksclient.get_projects(domain=domain)
    for p in projects:
        usage = novaclient.get_usage(project_id=p.id)
        if hasattr(usage, 'server_usages'):
            instance_count = len(usage.server_usages)
        else:
            instance_count = 0
        print '%s (instances: %s)' % (p.name, instance_count)
if options.action[0] == 'show':
    if options.project:
        project = ksclient.get_project(project=options.project, domain=domain)
        pp = pprint.PrettyPrinter(indent=1)
        pp.pprint(project.to_dict())
    else:
        print 'project name must be set to show project'
if options.action[0] == 'quota':
    if options.project:
        quota = ksclient.list_quota(project=options.project, domain=domain)
        pp = pprint.PrettyPrinter(indent=1)
        if 'compute' in quota:
            pp.pprint(quota['compute'].to_dict())
    else:
        print 'project name must be set to show quota'
