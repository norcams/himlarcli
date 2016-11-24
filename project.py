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
             '-t': { 'dest': 'type', 'help': 'project type (used for quota)', 'default': 'default', 'metavar': 'type'}}
options = utils.get_action_options(desc, actions, opt_args=opt_args)
ksclient = Keystone(options.config, debug=options.debug)
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
quota = himutils.load_config('config/quota.yaml')
domain='Dataporten'

if options.action[0] == 'create':
    if options.type not in quota:
        print 'Type %s unknown. Check config/quota.yaml' % options.type
    if options.project and options.user:
        if options.type == 'test':
            test = 1
        else:
            test = 0
        project = ksclient.create_project(domain=domain,
                                          project=options.project,
                                          admin=options.user,
                                          test=test,
                                          type=options.type,
                                          quota=quota[options.type])
        pp = pprint.PrettyPrinter(indent=1)
        if project:
            pp.pprint(project.to_dict())
            ksclient.grant_role(project=options.project,
                                user=options.user,
                                role='user',
                                domain=domain)
    else:
        print 'user and project name must be set to create project'
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
    projects = ksclient.list_projects(domain=domain)
    for p in projects:
        print p
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
