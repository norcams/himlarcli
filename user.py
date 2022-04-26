#!/usr/bin/env python
import sys
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.ldapclient import LdapClient
from himlarcli.mail import Mail
from himlarcli import utils as himutils
from datetime import datetime, date, timedelta
import time
import re

# OPS! It might need some updates. We use class Mail instead of Notify now.

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
ksclient.set_domain(options.domain)
logger = ksclient.get_logger()
printer = Printer(options.format)


def action_show():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        print("%s is not a valid user. Please check your spelling or case." % options.user)
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
    print("\nYou are about to rename user with email %s to %s" % (options.old, options.new))
    print("\nWhen a user changes affilation we need to change the following:")
    # new
    print(" * Delete %s-group if it exists" % options.new)
    print(" * Delete %s api user if it exists" % options.new.lower())
    print(" * Delete %s dataporten user if it exists" % options.new.lower())
    print(" * Delete %s demo project and instances if exists" % new_demo_project)
    print(" * Delete %s personal project and instances if exist" % personal)
    # old
    print(" * Rename group from %s-group to %s-group" % (options.old, options.new))
    print(" * Rename api user from %s to %s" % (options.old.lower(), options.new.lower()))
    print(" * Rename demo project from %s to %s" % (old_demo_project, new_demo_project))
    print(" * Delete old dataporten user %s" % (options.old))

    question = "\nAre you sure you will continue"
    if not himutils.confirm_action(question):
        return
    print('Please wait...')
    ksclient.user_cleanup(email=options.new)
    ksclient.rename_user(new_email=options.new,
                         old_email=options.old)

# pylint: disable=E1101
def action_deactivate():
    # disabled (trondham, 2022-04-21)
    print("This action is not in use")
    return

    if options.org == 'all':
        active, deactive, unknown = get_valid_users()
    else:
        active, deactive, unknown = get_valid_users(options.org)

    q = 'This will deactivate %s users (total active users %s)' \
        % (len(deactive), active['total'])
    if not himutils.confirm_action(q):
        return
    subject = '[UH-IaaS] Your account have been disabled'
    regions = ksclient.find_regions()
    count = 0
    users_deactivated = list()
    for email in deactive:
        user = ksclient.get_user_by_email(email, 'api')
        # Disable user and notify user
        if user.enabled:
            # notify user
            mail_user(email, 'notify/notify_deactivate.txt', subject)
            # Disable api user
            date = datetime.today().strftime('%Y-%m-%d')
            ksclient.update_user(user_id=user.id, enabled=False, disabled=date)
        else:
            continue
        projects = ksclient.get_user_projects(email)
        # Shutoff instances in demo and personal project.
        for project in projects:
            if not hasattr(project, 'type'):
                continue
            if project.type == 'demo' or project.type == 'personal':
                for region in regions:
                    nc = Nova(options.config, debug=options.debug, log=logger, region=region)
                    nc.set_dry_run(options.dry_run)
                    instances = nc.get_project_instances(project.id)
                    for i in instances:
                        if not options.dry_run:
                            count += 1
                            if i.status == 'ACTIVE':
                                i.stop()
                        nc.debug_log('stop instance %s' % i.id)
        users_deactivated.append(email)
    output = dict()
    output['header'] = 'Deactivated users:'
    output['users'] = users_deactivated
    printer.output_dict(output)
    output = dict()
    output['header'] = 'Stopped instances:'
    output['servers'] = count
    printer.output_dict(output)

def action_enable():
    """ Enable a user. The following happens when a user is enabled:
          * Projects for which the user is admin is removed from quarantine
          * API user is enabled
          * Dataporten user is enabled
        Version: 2022-04
    """
    if not ksclient.is_valid_user(email=options.user):
        himutils.sys_error('User %s not found as a valid user.' % options.user, 1)

    # get the user objects
    user = ksclient.get_user_objects(email=options.user, domain='api')

    # enable the user in API and Dataporten
    ksclient.enable_user(user['api'].id)
    ksclient.enable_user(user['dataporten'].id)

    # prefix prints with dry-run if that option is used
    if options.dry_run:
        print_prefix = "(dry-run) "
    else:
        print_prefix = ""

    # rename the user group
    group = ksclient.get_group_by_email(options.user)
    if group and group.name == "%s-disabled" % options.user:
        new_group_name = "%s-group" % options.user
        ksclient.update_group(group.id, name=new_group_name)
        print("%sGroup rename: %s-disabled -> %s-group" % (print_prefix, options.user, options.user))
    else:
        himutils.sys_error('WARNING: Could not find disabled group for user %s!' % options.user, 0)

    # remove quarantine from projects
    for project in user['projects']:
        if not hasattr(project, 'admin'):
            continue
        if project.admin != user['api'].name:
            continue
        ksclient.project_quarantine_unset(project.name)
        print('%sQuarantine unset for project: %s' % (print_prefix, project.name))

    # Print our success
    print("%sUser %s enabled (API)" % (print_prefix, user['api'].name))
    print("%sUser %s enabled (Dataporten)" % (print_prefix, user['dataporten'].name))

def action_disable():
    """ Disable a user. The following happens when a user is disabled:
          * Projects for which the user is admin is put into quarantine
          * API user is disabled
          * Dataporten user is disabled
        Version: 2022-04
    """
    if not ksclient.is_valid_user(email=options.user):
        himutils.sys_error('User %s not found as a valid user.' % options.user, 1)

    # prefix prints with dry-run if that option is used
    if options.dry_run:
        print_prefix = "(dry-run) "
    else:
        print_prefix = ""

    # ask for confirmation
    if not options.force:
        if not himutils.confirm_action('Disable user %s' % options.user):
            return

    if options.date:
        date = himutils.get_date(options.date, None, '%Y-%m-%d')
    else:
        date = datetime.now().strftime("%Y-%m-%d")

    # get the user objects
    user = ksclient.get_user_objects(email=options.user, domain='api')

    # loop through project list, and determine if the project can be
    # put into quarantine. Only put projects into quarantine if:
    #   - they are personal/demo projects
    #   - they are shared projects with only one member, and the
    #     member is same as admin
    problematic_projects = list()  # projects that are problematic
    quarantine_projects = list()   # projects to put in quarantine
    for project in user['projects']:
        if not hasattr(project, 'admin'):
            continue
        if project.admin != options.user:
            continue
        if hasattr(project, 'type') and (project.type == 'demo' or project.type == 'personal'):
            quarantine_projects.append(project.name)
            continue
        project_roles = ksclient.list_roles(project_name=project.name)
        if len(project_roles) > 1:
            problematic_projects.append(project.name)
            continue
        if len(project_roles) == 1 and project_roles[0]['group'].replace('-group', '') != options.user:
            problematic_projects.append(project.name)
            continue
        quarantine_projects.append(project.name)

    # exit with error if we found problematic projects
    if len(problematic_projects) > 0:
        error_msg = "ERROR: User %s is admin for %d shared projects with multiple users:\n\n" % (options.user, len(problematic_projects))
        for pname in problematic_projects:
            error_msg += "  - %s\n" % pname
        error_msg += "\nFix these before attemting a new user disable\n"
        error_msg += "FAILED! Can't disable user %s\n" % options.user
        himutils.sys_error(error_msg, 1)

    # put projects into quarantine
    quarantine_reason = {
        'deleted': 'deleted-user',
        'teppe':   'teppe'
    }
    for pname in quarantine_projects:
        ksclient.project_quarantine_set(pname, quarantine_reason[options.reason], date)
        print('%sQuarantine set for project: %s' % (print_prefix, pname))

    # disable the user in API and Dataporten
    ksclient.disable_user(user['api'].id, options.reason, date)
    ksclient.disable_user(user['dataporten'].id, options.reason, date)

    # rename the user group
    group = ksclient.get_group_by_email(options.user)
    if group and group.name == "%s-group" % options.user:
        new_group_name = "%s-disabled" % options.user
        ksclient.update_group(group.id, name=new_group_name)
        print("%sGroup rename: %s-group -> %s-disabled" % (print_prefix, options.user, options.user))
    else:
        himutils.sys_error('WARNING: Could not find group for user %s!' % options.user, 0)

    # Print our success
    print("%sUser %s disabled (API)" % (print_prefix, user['api'].name))
    print("%sUser %s disabled (Dataporten)" % (print_prefix, user['dataporten'].name))

def action_validate():
    if options.org == 'all':
        active, deactive, unknown = get_valid_users()
    else:
        active, deactive, unknown = get_valid_users(options.org)

    active['header'] = 'Validated active users:'
    printer.output_dict(active)
    output = dict()
    output['header'] = 'Users that should be deactivated:'
    output['users'] = deactive
    output['count'] = len(deactive)
    printer.output_dict(output)
    output = dict()
    output['header'] = 'Untested user orgs:'
    output['orgs'] = unknown
    printer.output_dict(output)

def action_list_disabled():
    users = ksclient.get_users(domain=options.domain, enabled=False)
    printer.output_dict({'header': 'Disabled user list (name, date reason)'})
    count = 0
    for user in users:
        if options.org != 'all':
            org = ksclient.get_user_org(user.name)
            if org and org != options.org:
                continue
        output = {
            '1': user.name,
            '2': user.disabled if hasattr(user, 'disabled') else 'unknown'
        }
        printer.output_dict(output, sort=True, one_line=True)
        count += 1
    printer.output_dict({'header': 'Count', 'disabled_users': count})

def action_purge():
    disabled_users = ksclient.get_users(domain=options.domain, enabled=False)
    purge_users = list()
    user_days = dict()
    today = date.today()
    for user in disabled_users:
        if not hasattr(user, 'disabled'):
            himutils.sys_error("WARNING: User %s is disabled without date and reason. IGNORING" % user.name, 0)
            continue

        # get the disable date and reason
        m = re.fullmatch(r'(\d\d\d\d-\d\d-\d\d) (\w+)', user.disabled)
        if m == None:
            himutils.sys_error("WARNING: User %s has garbled disabled string '%s'. IGNORING" % (user.name, user.disabled), 0)
            continue
        reason = m.group(2)
        disabled_date = himutils.get_date(m.group(1), None, '%Y-%m-%d')

        # only delete users with the given reason
        if reason != options.reason:
            continue

        # allow gracetime before we delete
        gracetime = timedelta(options.days)
        if today - disabled_date < gracetime:
            continue

        # only delete users with the given org
        if options.org != 'all':
            org = ksclient.get_user_org(user.name)
            if org and org != options.org:
                continue

        # ignore user if they are admin for other projects than demo, private
        user_has_projects = False
        this_user = ksclient.get_user_objects(email=user.name, domain='api')
        for project in this_user['projects']:
            if not hasattr(project, 'admin'):
                continue
            if not hasattr(project, 'type'):
                continue
            if project.type == 'demo' or project.type == 'personal':
                continue
            if project.admin == this_user['api'].name:
                user_has_projects = True
                break
        if user_has_projects:
            himutils.sys_error("WARNING: User %s is admin for shared projects. IGNORING" % user.name, 0)
            continue

        # limit how many are deleted at once
        if options.limit and len(purge_users) >= int(options.limit):
            break

        # store user and days disabled in dictionary
        purge_users.append(user)
        user_days[user.id] = (today - disabled_date).days

    # stop here if there are no users to delete
    if len(purge_users) == 0:
        print("Nothing to do. Zero users to delete")
        return

    # formulate question
    question = "Found %d disabled users that match the criteria:\n\n" % len(purge_users)
    for user in purge_users:
        question += "  %-4s  %s\n" % (str(user_days[user.id]), user.name)
    question += "\nDelete these users?"

    # ask for confirmation if not forced
    if not himutils.confirm_action(question):
        return

    # prefix prints with dry-run if that option is used
    if options.dry_run:
        print_prefix = "(dry-run) "
    else:
        print_prefix = ""

    # actually delete the users
    for user in purge_users:
        group = ksclient.get_group_by_email(user.name)
        if group and group.name == "%s-disabled" % user.name:
            new_group_name = "%s-group" % user.name
            ksclient.update_group(group.id, name=new_group_name)
        ksclient.user_cleanup(email=user.name)
        print("%sDeleted user: %s" % (print_prefix, user.name))

def action_password():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        himutils.sys_error("%s is not a valid user." % options.user, 1)
    print(ksclient.reset_password(email=options.user))

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
    if not options.force:
        if not himutils.confirm_action('Delete user and all instances for %s' % options.user):
            return
    print("We are now deleting user, group, project and instances for %s" % options.user)
    print('Please wait...')
    ksclient.user_cleanup(email=options.user)
    print('Delete successful')

def mail_user(email, template, subject):
    body_content = himutils.load_template(inputfile=template,
                                          mapping={'email': email},
                                          log=logger)
    mail = Mail(options.config, debug=False, log=logger)
    mail.set_dry_run(options.dry_run)
    mail.mail_user(body_content, subject, email)
    mail.close()

def get_valid_users(organization=None):
    whitelist = himutils.load_file('whitelist_users.txt', logger)
    if not whitelist:
        himutils.sys_error('Could not find whitelist_users.txt!')
    orgs = list(himutils.load_config('config/ldap.yaml', logger).keys())
    if organization and organization not in orgs:
        himutils.sys_error('Unknown org used: %s' % organization)
    ldap = dict()
    for o in orgs:
        ldap[o] = LdapClient(options.config, debug=options.debug, log=logger)
        ldap[o].bind(o)
    users = ksclient.list_users(domain=options.domain)
    deactive = list()
    active = dict()
    unknown = list()
    count = 0
    for user in users:
        if user in whitelist:
            ksclient.debug_log('user %s in whitelist' % user)
        org = ksclient.get_user_org(user)
        # Drop users if organization is set
        if organization and org != organization:
            continue
        # Only add a user to deactive if user also enabled in OS
        os_user = ksclient.get_user_by_email(user, 'api')
        if not os_user.enabled:
            continue
        if options.limit and count >= int(options.limit):
            break
        count += 1
        # user in valid org
        if org and org in orgs:
            if (not ldap[org].get_user(email=user, org=org)
                    and user not in whitelist):
                deactive.append(user)
                # Sleep after a ldap search
                time.sleep(2)
            else:
                active[org] = active.setdefault(org, 0) + 1
        else:
            if '@' in user:
                org = user.split("@")[1]
                if org not in unknown:
                    unknown.append(org)
    total = 0
    for k, v in active.items():
        total += v
    active['total'] = total
    return (active, deactive, unknown)

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
