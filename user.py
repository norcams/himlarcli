#!/usr/bin/env python
import sys
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=ksclient.get_logger())
printer = Printer(options.format)
domain = 'Dataporten'

def action_show():
    if not ksclient.is_valid_user(user=options.user, domain=domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    obj = ksclient.get_user_objects(email=options.user, domain=domain)
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
    users = ksclient.list_users(domain=domain)
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
    if not ksclient.is_valid_user(user=options.old, domain=domain):
        print "%s is not a valid user. Please check your spelling or case." % options.old
        sys.exit(1)
    print "\nYou are about to rename user with email %s to %s" % (options.old, options.new)
    print "\nWhen a user changes affilation we need to change the following:"
    print " * Delete %s-group if it exists" % options.new
    print " * Delete %s api user if it exists" % options.new.lower()
    print " * Delete %s dataporten user if it exists" % options.new.lower()
    print " * Delete %s demo/personal project if it exists" % options.new.lower()
    print " * Delete %s instances in demo/personal project if it exists" % options.new.lower()
    print " * !!! DELETE OLD DATAPORTEN USER %s !!!" % (options.old)
    print " * Rename group from %s-group to %s-group" % (options.old, options.new)
    print " * Rename api user from %s to %s" % (options.old.lower(), options.new.lower())
    print " * Rename personal project from %s to %s" % (options.old.lower(), options.new.lower())
    q = "\nAre you sure you will continue (yes|no)? "
    answer = raw_input(q)
    if answer.lower() == 'yes':
        print 'Please wait...'
        ksclient.remove_user(email=options.new,
                             domain=domain,
                             dry_run=options.dry_run)
        ksclient.rename_user(new_email=options.new,
                             old_email=options.old,
                             domain=domain,
                             dry_run=options.dry_run)
    else:
        print "You just dodged a bullet my friend!"

def action_password():
    if not ksclient.is_valid_user(user=options.user, domain=domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    ksclient.reset_password(email=options.user, domain=domain, dry_run=options.dry_run)

def action_delete():
    if not himutils.confirm_action('Delete user and all instances for %s' % options.user):
        return
    print "We are now deleting user, group, project and instances for %s" % options.user
    print 'Please wait...'
    result = ksclient.remove_user(email=options.user, domain=domain, dry_run=options.dry_run)
    if not result:
        print 'Delete failed! Run with debug for more information'
    else:
        print 'Delete successfull'

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Action %s not implemented" % options.action)
    sys.exit(1)
action()
