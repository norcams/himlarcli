#!/usr/bin/env python
import sys
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.ldapclient import LdapClient
from himlarcli import utils as himutils
from datetime import datetime
import time

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
ksclient.set_domain(options.domain)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
printer = Printer(options.format)

def action_show():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    obj = ksclient.get_user_objects(email=options.user, domain=options.domain)
    obj_type = options.obj_type
    if obj_type not in obj:
        return
    if obj_type == 'projects':
        for project in obj[obj_type]:
            objects = project.to_dict()
            objects['__obj_type'] = type(project).__name__
            objects['header'] = "%s (%s)" % (objects['__obj_type'], obj_type.upper())
            printer.output_dict(objects)
    else:
        objects = obj[obj_type].to_dict()
        objects['__obj_type'] = type(obj[obj_type]).__name__
        objects['header'] = "%s (%s)" % (objects['__obj_type'], obj_type.upper())
        printer.output_dict(objects)

def action_list():
    users = ksclient.list_users(domain=options.domain)
    domains = dict()
    output = dict({'users': list()})
    for user in users:
        if '@' in user:
            output['users'].append(user)
            org = user.split("@")[1]
            if org in domains:
                domains[org] += 1
            else:
                domains[org] = 1
    output['header'] = 'Registered users:'
    printer.output_dict(output)
    domains['header'] = 'Email domains:'
    printer.output_dict(domains)

def action_rename():
    if not ksclient.is_valid_user(email=options.old):
        himutils.sys_error('User %s not found as a valid user.' % options.old)
    personal = ksclient.get_project_name(options.new, prefix='PRIVATE')
    new_demo_project = ksclient.get_project_name(options.new)
    old_demo_project = ksclient.get_project_name(options.old)
    print "\nYou are about to rename user with email %s to %s" % (options.old, options.new)
    print "\nWhen a user changes affilation we need to change the following:"
    # new
    print " * Delete %s-group if it exists" % options.new
    print " * Delete %s api user if it exists" % options.new.lower()
    print " * Delete %s dataporten user if it exists" % options.new.lower()
    print " * Delete %s demo project and instances if exists" % new_demo_project
    print " * Delete %s personal project and instances if exist" % personal
    # old
    print " * Rename group from %s-group to %s-group" % (options.old, options.new)
    print " * Rename api user from %s to %s" % (options.old.lower(), options.new.lower())
    print " * Rename demo project from %s to %s" % (old_demo_project, new_demo_project)
    print " * Delete old dataporten user %s" % (options.old)

    question = "\nAre you sure you will continue"
    if not himutils.confirm_action(question):
        return
    print 'Please wait...'
    ksclient.user_cleanup(email=options.new)
    ksclient.rename_user(new_email=options.new,
                         old_email=options.old)

def action_validate():
    orgs = himutils.load_config('config/ldap.yaml', logger).keys()
    ldap = dict()
    for org in orgs:
        ldap[org] = LdapClient(options.config, debug=options.debug)
        ldap[org].bind(org)
    users = ksclient.list_users(domain=options.domain)
    deactive = list()
    unknown = list()
    for user in users:
        org_found = False
        for org in orgs:
            if not org in user:
                continue
            org_found = True
            if not ldap[org].get_user(user):
                #print "%s not found in ldap" % user
                deactive.append(user)
            break
        if not org_found:
            #print "%s org not found" % user
            if '@' in user:
                org = user.split("@")[1]
                unknown.append(org)
        time.sleep(2)
    output = dict()
    output['header'] = 'Unknown user orgs:'
    output['orgs'] = unknown
    printer.output_dict(output)
    output = dict()
    output['header'] = 'Deactive users:'
    output['users'] = deactive
    output['count'] = len(deactive)
    printer.output_dict(output)

def action_password():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        himutils.sys_error("%s is not a valid user." % options.user, 1)
    print ksclient.reset_password(email=options.user)

def action_create():
    if not ksclient.is_valid_user(email=options.admin, domain=options.domain):
        himutils.sys_error('%s is not a valid user. Admin must be a valid user' % options.admin, 1)
    if options.enddate:
        try:
            enddate = datetime.strptime(options.enddate, '%d.%m.%y').date()
        except ValueError:
            himutils.sys_error('date format DD.MM.YY not valid for %s' % options.enddate, 1)
    else:
        enddate = None
    email = options.email if options.email else options.user
    ksclient.create_user(name=options.user,
                         email=email,
                         password=options.password,
                         admin=options.admin,
                         description=options.description,
                         enddate=str(enddate))

def action_delete():
    if not ksclient.is_valid_user(email=options.user):
        himutils.sys_error('User %s not found as a valid user.' % options.user)
    if not himutils.confirm_action('Delete user and all instances for %s' % options.user):
        return
    print "We are now deleting user, group, project and instances for %s" % options.user
    print 'Please wait...'
    ksclient.user_cleanup(email=options.user)
    print 'Delete successful'

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Action %s not implemented" % options.action)
    sys.exit(1)
action()
