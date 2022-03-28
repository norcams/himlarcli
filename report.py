#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli import utils
from prettytable import PrettyTable
from datetime import datetime
from datetime import timedelta
import re
import sys
import json
import os

utils.is_virtual_env()

parser = Parser()
parser.set_autocomplete(True)
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
    utils.sys_error('no regions found with this name!')

#---------------------------------------------------------------------
# Main functions
#---------------------------------------------------------------------
def action_show():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        utils.sys_error('No project found with name %s' % options.project)
    sys.stdout.write(Printer.prettyprint_project_metadata(project, options, logger, regions))
    if options.detail:
        sys.stdout.write(Printer.prettyprint_project_zones(project, options, logger))
        sys.stdout.write(Printer.prettyprint_project_volumes(project, options, logger, regions))
        sys.stdout.write(Printer.prettyprint_project_images(project, options, logger, regions))
        sys.stdout.write(Printer.prettyprint_project_instances(project, options, logger, regions))

def action_list():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(**search_filter)

    # Project counter
    count = 0

    # Loop through projects
    for project in projects:
        sys.stdout.write(Printer.prettyprint_project_metadata(project, options, logger, regions))
        if options.detail:
            sys.stdout.write(Printer.prettyprint_project_zones(project, options, logger))
            sys.stdout.write(Printer.prettyprint_project_volumes(project, options, logger, regions))
            sys.stdout.write(Printer.prettyprint_project_images(project, options, logger, regions))
            sys.stdout.write(Printer.prettyprint_project_instances(project, options, logger, regions))

        # Print some vertical space and increase project counter
        print "\n\n"
        count += 1

    # Finally print out number of projects
    printer.output_dict({'header': 'Project list count', 'count': count})

def action_user():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    user = ksclient.get_user_objects(email=options.user, domain=options.domain)

    # Project counter
    count = 0

    for project in user['projects']:
        if options.admin and project.admin != options.user:
            continue
        sys.stdout.write(Printer.prettyprint_project_metadata(project, options, logger, regions, options.user))
        if options.detail:
            sys.stdout.write(Printer.prettyprint_project_zones(project, options, logger))
            sys.stdout.write(Printer.prettyprint_project_volumes(project, options, logger, regions))
            sys.stdout.write(Printer.prettyprint_project_images(project, options, logger, regions))
            sys.stdout.write(Printer.prettyprint_project_instances(project, options, logger, regions))

        # Print some vertical space and increase project counter
        print "\n\n"
        count += 1

    # Finally print out number of projects
    printer.output_dict({'header': 'Project list count', 'count': count})

def action_vendorapi():
    data = vendorapi_list()
    data_project  = data[0]
    data_instance = data[1]

    if options.outdir:
        file_projects = os.path.join(options.outdir, 'project.json')
        file_instances = os.path.join(options.outdir, 'instances.json')
        with open(file_projects, "w") as outfile:
            json.dump(data_project, outfile)
        with open(file_instances, "w") as outfile:
            json.dump(data_instance, outfile)
    else:
        projects_object  = json.dumps(data_project, indent = 4)
        instances_object = json.dumps(data_instance, indent = 4)
        print 'PROJECTS'
        print '-----------------------------------------------------------------------------'
        print projects_object
        print
        print 'INSTANCES'
        print '-----------------------------------------------------------------------------'
        print instances_object

def action_mail():
    if not options.template:
        utils.sys_error("Option '--template' is required when sending mail")
        sys.exit(1)

    if options.mail_user:
        if not ksclient.is_valid_user(email=options.mail_user, domain=options.domain):
            print "%s is not a valid user. Please check your spelling or case." % options.mail_user
            sys.exit(1)
        users = [options.mail_user]
    else:
        users = ksclient.list_users(domain=options.domain)

    # We want details
    options.detail = True

    # Attachment dict
    attachment = dict()

    # Admin/member dict
    admin = dict()
    member = dict()

    # Project counter
    project_counter = 0

    # Ask for confirmation
    if not options.force and not options.dry_run:
        if not utils.confirm_action('Send mail to (potentially) %d users?' % len(users)):
            return

    # Loop through projects
    for user in users:
        # Ignore system users
        if not '@' in user:
            continue

        # Get user object
        this_user = ksclient.get_user_objects(email=user, domain=options.domain)
        if not this_user:
            continue

        # Ignore users who only have a DEMO project, i.e. number of
        # projects is equal or less than 1
        if len(this_user['projects']) <= 1:
            continue

        # Set common mail parameters
        mail = utils.get_client(Mail, options, logger)
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)
        if options.fromaddr:
            fromaddr = options.fromaddr
        else:
            fromaddr = 'support@nrec.no'

        # Loop through projects collecting info
        attachment_payload = ''
        admin_counter = 0
        member_counter = 0
        for project in this_user['projects']:
            attachment_payload += Printer.prettyprint_project_metadata(project, options, logger, regions, user)
            attachment_payload += Printer.prettyprint_project_zones(project, options, logger)
            attachment_payload += Printer.prettyprint_project_volumes(project, options, logger, regions)
            attachment_payload += Printer.prettyprint_project_images(project, options, logger, regions)
            attachment_payload += Printer.prettyprint_project_instances(project, options, logger, regions)

            # Add some vertical space
            attachment_payload += "\n\n"

            # Increase counters
            if project.admin == user:
                admin_counter += 1
            else:
                member_counter += 1

        # Construct mail content
        body_content = utils.load_template(inputfile=options.template,
                                           mapping={'admin_count': admin_counter,
                                                    'member_count': member_counter},
                                           log=logger)
        msg = mail.create_mail_with_txt_attachment(options.subject,
                                                   body_content,
                                                   attachment_payload,
                                                   'resources.txt',
                                                   fromaddr)
        # Send mail to user
        mail.send_mail(user, msg, fromaddr)
        if options.dry_run:
            print "Did NOT send spam to %s" % user
            print "    --> admin for %d projects, member of %d projects" % (admin_counter, member_counter)
        else:
            print "Spam sent to %s" % user

def action_enddate():
    if not options.list and not options.template:
        utils.sys_error("Option '--template' is required when sending mail")
        sys.exit(1)

    if not options.list and not options.days:
        utils.sys_error("Option '--days' is required")
        sys.exit(1)

    search_filter = dict()
    projects = ksclient.get_projects(**search_filter)

    today = datetime.today()

    options.detail = True # we want details

    if options.list and not options.days:
        project_list = dict()
        for project in projects:
            project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
            project_type = project.type if hasattr(project, 'type') else 'None'

            # Ignore DEMO projects
            if project_type == 'demo':
                continue

            # Ignore already quarantined projects
            if ksclient.check_project_tag(project.id, 'quarantine_active'):
                continue

            # Ignore projects without an enddate
            if project_enddate == 'None':
                continue

            # Get current enddate
            enddate = datetime.strptime(project.enddate, '%Y-%m-%d')

            # store data
            project_list[project.name] = (enddate - today).days

        #PY3: for project in dict(sorted(project_list.items(), key=lambda item: item[1])):
        for project in project_list:
            print "%-4s %s" % (project_list[project], project)
        return

    for project in projects:
        project_type = project.type if hasattr(project, 'type') else 'None'
        project_admin = project.admin if hasattr(project, 'admin') else 'None'
        project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
        project_org = project.org if hasattr(project, 'org') else 'None'
        project_contact = project.contact if hasattr(project, 'contact') else 'None'

        # Ignore DEMO projects
        if project_type == 'demo':
            continue

        # Ignore already quarantined projects
        if ksclient.check_project_tag(project.id, 'quarantine_active'):
            continue

        # Ignore projects without an enddate
        if project_enddate == 'None':
            continue

        # Get current enddate
        enddate = datetime.strptime(project.enddate, '%Y-%m-%d')

        # Set common mail parameters
        mail = utils.get_client(Mail, options, logger)
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)
        if options.fromaddr:
            fromaddr = options.fromaddr
        else:
            fromaddr = 'support@nrec.no'
        if project_contact != 'None':
            ccaddr = project_contact
        else:
            ccaddr = None

        for days in options.days:
            days = int(days)
            if (enddate - today).days == days:

                if options.list:
                    print "%-4s %s" % (days, project.name)
                else:
                    options.admin = project_admin  # for prettyprint_project_metadata()

                    attachment_payload = ''
                    attachment_payload += Printer.prettyprint_project_metadata(project, options, logger, regions, project_admin)
                    attachment_payload += Printer.prettyprint_project_zones(project, options, logger)
                    attachment_payload += Printer.prettyprint_project_volumes(project, options, logger, regions)
                    attachment_payload += Printer.prettyprint_project_images(project, options, logger, regions)
                    attachment_payload += Printer.prettyprint_project_instances(project, options, logger, regions)

                    # Construct mail content
                    if days > 0:
                        subject = 'NREC: End date in %d days for project "%s"' % (days, project.name)
                        body_content = utils.load_template(inputfile=options.template,
                                                           mapping={'project': project.name,
                                                                    'enddate': project_enddate,
                                                                    'days': days},
                                                           log=logger)
                        msg = mail.create_mail_with_txt_attachment(subject,
                                                                   body_content,
                                                                   attachment_payload,
                                                                   'resources.txt',
                                                                   fromaddr,
                                                                   ccaddr)
                    else:
                        subject = 'NREC: Project "%s" will be deleted in %d days' % (project.name, 90 + days)
                        body_content = utils.load_template(inputfile=options.template,
                                                           mapping={'project': project.name,
                                                                    'enddate': project_enddate,
                                                                    'ago': -days,
                                                                    'days': 90 + days},
                                                           log=logger)
                        msg = mail.create_mail_with_txt_attachment(subject,
                                                                   body_content,
                                                                   attachment_payload,
                                                                   'resources.txt',
                                                                   fromaddr,
                                                                   ccaddr)

                    # Send mail to user
                    mail.send_mail(project_admin, msg, fromaddr)
                    if options.dry_run:
                        print "Did NOT send spam to %s;" % project_admin
                        print "Subject: %s" % subject
                        print "To: %s" % project_admin
                        if ccaddr:
                            print "Cc: %s" % ccaddr
                        print "From: %s" % fromaddr
                        print '---'
                        print body_content
                    else:
                        print "Spam sent to %s" % project_admin


#---------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------

def vendorapi_list():
    from himlarcli.nova import Nova

    data_instance = dict()
    data_project  = dict()

    projects = ksclient.get_projects()

    # Loop through projects
    for project in projects:
        contact = project.contact if hasattr(project, 'contact') else None
        admin = project.admin if hasattr(project, 'admin') else None
        data_project[project.id] = {
            "project_name": project.name,
            "project_admin": admin,
            "project_contact": contact
        }
        # Get Instances
        for region in regions:
            instances = dict()
            # Initiate Nova object
            nc = utils.get_client(Nova, options, logger, region)

            # Get a list of instances in project
            instances[region] = nc.get_project_instances(project_id=project.id)
            for instance in instances[region]:
                contact = project.contact if hasattr(project, 'contact') else None
                data_instance[instance.id] = {
                    "region": region,
                }

    return data_project, data_instance

#=====================================================================
# Main program
#=====================================================================
# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
