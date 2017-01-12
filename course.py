#!/usr/bin/python
import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils

# Input args
desc = 'Mange student course project'
actions = ['create']
opt_args = { '-n': { 'dest': 'name', 'help': 'course name', 'metavar': 'name'},
             '-u': { 'dest': 'user', 'help': 'email of teacher', 'metavar': 'user'},
             '-f': { 'dest': 'file', 'help': 'file with students', 'metavar': 'file'}}

options = utils.get_action_options(desc, actions, opt_args=opt_args)
ksclient = Keystone(options.config, debug=options.debug)
#novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
quota = himutils.load_config('config/quota.yaml', log=ksclient.get_logger())

domain='Dataporten'

if options.action[0] == 'create':
    if options.name and options.user and options.file:
        students = himutils.load_file(options.file, log=ksclient.get_logger())
        pp = pprint.PrettyPrinter(indent=1)
        # Create owner project
        project_name = '%s-%s' % (options.name, options.user.lower())
        project = ksclient.create_project(domain=domain,
                                          project=project_name,
                                          admin=options.user,
                                          test=0,
                                          type='course',
                                          quota=quota['course'])
        ksclient.grant_role(project=project_name,
                            user=options.user,
                            role='superuser',
                            domain=domain)

        # Create student projects
        for student in students:
            project_name = '%s-%s' % (options.name, student.lower())
            project = ksclient.create_project(domain=domain,
                                              project=project_name,
                                              admin=options.user,
                                              test=0,
                                              type='course',
                                              quota=quota['course'])
            if project:
                pp.pprint(project.to_dict())
                # Grant student access
                ksclient.grant_role(project=project_name,
                                    user=student,
                                    role='user',
                                    domain=domain)
                # Grant admin access as owner
                ksclient.grant_role(project=project_name,
                                    user=options.user,
                                    role='user',
                                    domain=domain)
    else:
        print 'student file, user and project name must be set to create project'
elif options.action[0] == 'list':
    projects = ksclient.list_projects(domain=domain)
    for p in projects:
        print p
elif options.action[0] == 'show':
    if options.name:
        project = ksclient.get_project(project=options.name, domain=domain)
        pp = pprint.PrettyPrinter(indent=1)
        pp.pprint(project.to_dict())
    else:
        print 'name must be set to show project'
