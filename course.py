#!/usr/bin/python
import sys
import utils
import pprint
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli import utils as himutils

# Input args
desc = 'Mange student course project'
actions = ['create', 'list', 'delete']
opt_args = { '-n': { 'dest': 'name', 'help': 'course name (mandatory)', 'required': True, 'metavar': 'name'},
             '-u': { 'dest': 'user', 'help': 'email of teacher', 'metavar': 'user'},
             '-q': { 'dest': 'quota', 'help': 'project quota', 'default': 'course', 'metavar': 'quota'},
             '-f': { 'dest': 'file', 'help': 'file with students', 'metavar': 'file'}}

options = utils.get_action_options(desc, actions, dry_run=True, opt_args=opt_args)
ksclient = Keystone(options.config, debug=options.debug)
quota = himutils.load_config('config/quota.yaml', log=ksclient.get_logger())
project_types = himutils.load_config('config/type.yaml', log=ksclient.get_logger())
domain='Dataporten'

if options.action[0] == 'create':
    if options.user and options.file:
        if not ksclient.is_valid_user(user=options.user, domain=domain):
            print "ERROR! %s is not a valid user. Group from access not found!" % options.user
            sys.exit(1)
        students = himutils.load_file(options.file, log=ksclient.get_logger())
        pp = pprint.PrettyPrinter(indent=1)
        # Create owner project
        project_name = '%s-%s' % (options.name, options.user.lower())
        if not options.dry_run:
            project = ksclient.create_project(domain=domain,
                                              project=project_name,
                                              admin=options.user,
                                              test=0,
                                              course=options.name,
                                              type='education',
                                              quota=quota[options.quota])
            ksclient.grant_role(project=project_name,
                                user=options.user,
                                role='superuser',
                                domain=domain)

        # Create student projects
        for student in students:
            project_name = '%s-%s' % (options.name, student.lower())
            if not options.dry_run:
                project = ksclient.create_project(domain=domain,
                                                  project=project_name,
                                                  admin=options.user,
                                                  test=0,
                                                  course=options.name,
                                                  type='education',
                                                  quota=quota[options.quota])
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
        print 'student file (-f) and user (-u) must be set to create course project'
elif options.action[0] == 'list':
    projects = ksclient.get_projects(domain=domain, course=options.name)
    pp = pprint.PrettyPrinter(indent=1)
    for project in projects:
        if "%s-%s" % (options.name, project.admin.lower()) == project.name:
            print "TEACHER=%s" % project.name
            if options.debug:
                pp.pprint(project.to_dict())
        else:
            print "STUDENT=%s" % project.name
            if options.debug:
                pp.pprint(project.to_dict())
elif options.action[0] == 'delete':
    projects = ksclient.get_projects(domain=domain, course=options.name)
    q = "Delete projects and all instances for %s (yes|no)? " % options.name
    answer = raw_input(q)
    if answer.lower() == 'yes':
        print "Deleting %s projects for %s" % (len(projects), options.name)
        print 'Please wait...'
        for project in projects:
            if not options.dry_run:
                ksclient.delete_project(project.name, domain=domain)
    else:
        print "You just dodged a bullet my friend!"
