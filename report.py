#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli import utils as himutils
from prettytable import PrettyTable
from datetime import date
from datetime import datetime
from datetime import timedelta
import re
import sys
import json
import os
import csv

himutils.is_virtual_env()

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
    himutils.fatal('no regions found with this name!')

#---------------------------------------------------------------------
# Main functions
#---------------------------------------------------------------------
def action_show():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        himutils.fatal(f"No project found with name {options.project}")
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
        print("\n\n")
        count += 1

    # Finally print out number of projects
    printer.output_dict({'header': 'Project list count', 'count': count})

def action_resources():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(**search_filter)

    # Project counter
    count = 0

    # Loop through projects
    csv_output = []
    for project in projects:
        kc = Keystone(options.config, debug=options.debug)
        kc.set_dry_run(options.dry_run)
        kc.set_domain(options.domain)

        project_type = project.type if hasattr(project, 'type') else '(unknown)'
        project_admin = project.admin if hasattr(project, 'admin') else '(unknown)'
        project_created = project.createdate if hasattr(project, 'createdate') else '(unknown)'
        project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
        project_contact = project.contact if hasattr(project, 'contact') else 'None'
        project_roles = kc.list_roles(project_name=project.name)
        project_org = project.org if hasattr(project, 'org') else 'None'

        # Make project create date readable
        project_created = re.sub(r'T\d\d:\d\d:\d\d.\d\d\d\d\d\d', '', project_created)

        # Count users
        users = dict()
        users['user'] = 0
        users['object'] = 0
        users['superuser'] = 0
        if len(project_roles) > 0:
            for role in project_roles:
                users[role['role']] += 1

        # Count resources
        zones     = Printer._count_project_zones(project, options, logger)
        volumes   = Printer._count_project_volumes(project, options, logger, regions)
        images    = Printer._count_project_images(project, options, logger, regions)
        instances = Printer._count_project_instances(project, options, logger, regions)

        # Get resources used by instances and volumes
        ram   = dict()
        disk  = dict()
        vcpus = dict()
        hdd   = dict()
        ssd   = dict()
        for region in regions:
            # Initiate Nova object
            nc = himutils.get_client(Nova, options, logger, region)
            # Initiate Cinder object
            cc = himutils.get_client(Cinder, options, logger, region)

            ram[region]   = 0
            disk[region]  = 0
            vcpus[region] = 0
            hdd[region]   = 0
            ssd[region]   = 0

            for instance in nc.get_project_instances(project_id=project.id):
                ram[region]   += instance.flavor['ram']
                disk[region]  += instance.flavor['disk']
                vcpus[region] += instance.flavor['vcpus']

            for volume in cc.get_volumes(detailed=True, search_opts={'project_id': project.id}):
                if volume.volume_type == 'mass-storage-ssd':
                    ssd[region] += volume.size
                else:
                    hdd[region] += volume.size

        # Output array
        output_project = {
            #'header':              'Project Resources',
            'project_name':         project.name,
            'project_id':           project.id,
            'project_type':         project_type,
            'project_org':          project_org,
            'project_admin':        project_admin,
            'project_contact':      project_contact,
            'project_enddate':      project_enddate,
            'project_description':  project.description,
            'num_users':            users['user'],
            'num_object_users':     users['object'],
            'num_zones':            zones,
            'bgo_num_instances':    instances['bgo'],
            'osl_num_instances':    instances['osl'],
            'bgo_num_volumes':      volumes['bgo'],
            'osl_num_volumes':      volumes['osl'],
            'bgo_num_images':       images['bgo'],
            'osl_num_images':       images['osl'],
            'bgo_instance_ram_mb':  ram['bgo'],
            'osl_instance_ram_mb':  ram['osl'],
            'bgo_instance_disk_gb': disk['bgo'],
            'osl_instance_disk_gb': disk['osl'],
            'bgo_instance_vcpus':   vcpus['bgo'],
            'osl_instance_vcpus':   vcpus['osl'],
            'bgo_volume_hdd_gb':    hdd['bgo'],
            'osl_volume_hdd_gb':    hdd['osl'],
            'bgo_volume_ssd_gb':    ssd['bgo'],
            'osl_volume_ssd_gb':    ssd['osl'],
        }

        # Store results (CSV) or print (TEXT / JSON)
        if options.format == 'csv':
            csv_output.append(output_project)
        else:
            printer.output_dict(output_project, sort=True, one_line=True)

        # Increase project counter
        count += 1

    # Print results (CSV) or number of projects (TEXT / JSON)
    if options.format == 'csv':
        writer = csv.DictWriter(sys.stdout, fieldnames=csv_output[0].keys(), dialect='unix')
        writer.writeheader()
        for row in csv_output:
            writer.writerow(row)
    else:
        printer.output_dict({'header': 'Project list count', 'count': count})

def action_user():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        print("%s is not a valid user. Please check your spelling or case." % options.user)
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
        print("\n\n")
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
        print('PROJECTS')
        print('-----------------------------------------------------------------------------')
        print(projects_object)
        print()
        print('INSTANCES')
        print('-----------------------------------------------------------------------------')
        print(instances_object)

def action_mail():
    if not options.template:
        himutils.fatal("Option '--template' is required when sending mail")

    if options.mail_user:
        if not ksclient.is_valid_user(email=options.mail_user, domain=options.domain):
            himutils.fatal(f"{options.mail_user} is not a valid user. Please check your spelling or case.")
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
        if not himutils.confirm_action('Send mail to (potentially) %d users?' % len(users)):
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

        # Ignore disabled users
        if ksclient.is_disabled_user(user):
            continue

        # Ignore users who only have a DEMO project, i.e. number of
        # projects is equal or less than 1
        if len(this_user['projects']) <= 1:
            continue

        # Set common mail parameters
        mail = himutils.get_client(Mail, options, logger)
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
            if hasattr(project, 'admin') and project.admin == user:
                admin_counter += 1
            else:
                member_counter += 1

        # Construct mail content
        body_content = himutils.load_template(inputfile=options.template,
                                              mapping={'admin_count': admin_counter,
                                                       'member_count': member_counter},
                                              log=logger)
        msg = mail.create_mail_with_txt_attachment(options.subject,
                                                   body_content,
                                                   attachment_payload,
                                                   'resources.txt',
                                                   fromaddr)
        # Send mail to user
        mail.send_mail(user, msg, fromaddr, msgid='report')
        if options.dry_run:
            print("Did NOT send spam to %s" % user)
            print("    --> admin for %d projects, member of %d projects" % (admin_counter, member_counter))
        else:
            print("Spam sent to %s" % user)

def action_enddate():
    if not options.list and not options.template:
        himutils.fatal("Option '--template' is required when sending mail")

    if not options.list and not options.days:
        himutils.fatal("Option '--days' is required")

    search_filter = dict()
    projects = ksclient.get_projects(**search_filter)

    # Create datetime object for today at midnight
    dt = date.today()
    today = datetime.combine(dt, datetime.min.time())

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

        for project in dict(sorted(project_list.items(), key=lambda item: item[1])):
            print("%-4s %s" % (project_list[project], project))
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
        mail = himutils.get_client(Mail, options, logger)
        mail = Mail(options.config, debug=options.debug)
        mail.set_dry_run(options.dry_run)
        bccaddr = 'iaas-logs@usit.uio.no'
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
                    print("%-4s %s" % (days, project.name))
                else:
                    options.admin = project_admin  # for prettyprint_project_metadata()

                    attachment_payload = ''
                    attachment_payload += Printer.prettyprint_project_metadata(project, options, logger, regions, project_admin)
                    attachment_payload += Printer.prettyprint_project_zones(project, options, logger)
                    attachment_payload += Printer.prettyprint_project_volumes(project, options, logger, regions)
                    attachment_payload += Printer.prettyprint_project_images(project, options, logger, regions)
                    attachment_payload += Printer.prettyprint_project_instances(project, options, logger, regions)

                    # Construct mail content
                    subject = '[NREC] Project "%s" expires in %d days' % (project.name, days)
                    body_content = himutils.load_template(inputfile=options.template,
                                                          mapping={'project': project.name,
                                                                   'enddate': project_enddate,
                                                                   'days': days},
                                                          log=logger)
                    msg = mail.create_mail_with_txt_attachment(subject,
                                                               body_content,
                                                               attachment_payload,
                                                               'resources.txt',
                                                               fromaddr,
                                                               ccaddr,
                                                               bccaddr)

                    # Send mail to user
                    mail.send_mail(project_admin, msg, fromaddr, ccaddr, bccaddr, msgid='enddate')
                    if options.dry_run:
                        print("Did NOT send spam to %s;" % project_admin)
                        print("Subject: %s" % subject)
                        print("To: %s" % project_admin)
                        if ccaddr:
                            print("Cc: %s" % ccaddr)
                        if bccaddr:
                            print("Bcc: %s" % bccaddr)
                        print("From: %s" % fromaddr)
                        print('---')
                        print(body_content)
                    else:
                        print("Spam sent to %s" % project_admin)


def action_quarantine():
    if not options.list and not options.template:
        himutils.fatal("Option '--template' is required when sending mail")

    if not options.list and not options.days:
        himutils.fatal("Option '--days' is required when sending mail")

    # Create datetime object for today at midnight
    dt = date.today()
    today = datetime.combine(dt, datetime.min.time())

    # Search for projects
    search_filter = dict()
    search_filter['tags'] = ['quarantine_active', 'quarantine type: enddate']
    if options.days:
        search_filter['tags_any'] = list()
        for days in options.days:
            thisdate = (today - timedelta(days=int(days))).strftime('%Y-%m-%d')
            search_filter['tags_any'].append("quarantine date: %s" % thisdate)
    projects = ksclient.get_projects(**search_filter)

    # we want details
    options.detail = True

    # Set common mail parameters
    mail = himutils.get_client(Mail, options, logger)
    mail = Mail(options.config, debug=options.debug)
    mail.set_dry_run(options.dry_run)
    if options.fromaddr:
        fromaddr = options.fromaddr
    else:
        fromaddr = 'support@nrec.no'

    for project in projects:
        project_enddate = project.enddate if hasattr(project, 'enddate') else 'None'
        project_type = project.type if hasattr(project, 'type') else 'None'

        # Ignore DEMO projects
        if project_type == 'demo':
            continue

        # Output error if project is enabled (shouldn't happen)
        if project.enabled:
            himutils.warning(f"Project {project.name} has quarantine tags but is enabled")
            continue

        # Get quarantine info
        tags = ksclient.list_project_tags(project.id)
        r_date = re.compile('^quarantine date: .+$')
        date_tags = list(filter(r_date.match, tags))
        if len(date_tags) > 1:
            himutils.error(f"Too many quarantine dates for project {project.name}")
            continue
        elif len(date_tags) < 1:
            himutils.error(f"No quarantine date for project {project.name}")
            continue
        m_date = re.match(r'^quarantine date: (\d\d\d\d-\d\d-\d\d)$', date_tags[0])
        quarantine_date_iso = m_date.group(1)

        quarantine_date = datetime.strptime(quarantine_date_iso, "%Y-%m-%d")
        if options.list and not options.days:
            print("%-4s %s" % ((today - quarantine_date).days, project.name))
        else:
            for days in options.days:
                days = int(days)
                if (today - quarantine_date).days == days:
                    if options.list:
                        print("%-4s %s" % (days, project.name))
                    else:
                        project_contact = project.contact if hasattr(project, 'contact') else 'None'
                        bccaddr = 'iaas-logs@usit.uio.no'
                        if project_contact != 'None':
                            ccaddr = project_contact
                        else:
                            ccaddr = None

                        project_admin = project.admin if hasattr(project, 'admin') else 'None'
                        options.admin = project_admin  # for prettyprint_project_metadata()
                        attachment_payload = ''
                        attachment_payload += Printer.prettyprint_project_metadata(project, options, logger, regions, project_admin)
                        attachment_payload += Printer.prettyprint_project_zones(project, options, logger)
                        attachment_payload += Printer.prettyprint_project_volumes(project, options, logger, regions)
                        attachment_payload += Printer.prettyprint_project_images(project, options, logger, regions)
                        attachment_payload += Printer.prettyprint_project_instances(project, options, logger, regions)

                        # Construct mail content
                        subject = '[NREC] Project "%s" will be deleted in %d days' % (project.name, 90 - days)
                        body_content = himutils.load_template(inputfile=options.template,
                                                              mapping={'project': project.name,
                                                                       'enddate': project_enddate,
                                                                       'ago': days,
                                                                       'days': 90 - days},
                                                              log=logger)
                        msg = mail.create_mail_with_txt_attachment(subject,
                                                                   body_content,
                                                                   attachment_payload,
                                                                   'resources.txt',
                                                                   fromaddr,
                                                                   ccaddr,
                                                                   bccaddr)

                        # Send mail to user
                        mail.send_mail(project_admin, msg, fromaddr, ccaddr, bccaddr, msgid='quarantine')
                        if options.dry_run:
                            print("Did NOT send spam to %s;" % project_admin)
                            print("Subject: %s" % subject)
                            print("To: %s" % project_admin)
                            if ccaddr:
                                print("Cc: %s" % ccaddr)
                            if bccaddr:
                                print("Bcc: %s" % bccaddr)
                            print("From: %s" % fromaddr)
                            print('---')
                            print(body_content)
                        else:
                            print("Spam sent to %s" % project_admin)


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
            nc = himutils.get_client(Nova, options, logger, region)

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
    himutils.fatal("Function action_%s() not implemented" % options.action)
action()
