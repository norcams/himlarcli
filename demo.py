#!/usr/bin/env python

from datetime import date, datetime, timedelta
from email.mime.text import MIMEText
from prettytable import PrettyTable
import progressbar

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.cinder import Cinder
from himlarcli.mail import Mail
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.global_state import GlobalState, DemoInstance
from himlarcli.color import Color

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
regions = himutils.get_regions(options, kc)

# Logfile
logfile = f'logs/demo-expired-instances.log'

# Initialize database connection
db = himutils.get_client(GlobalState, options, logger)

# Age and notification config
MAX_AGE             = 90 # Max age of a demo instance, in days
FIRST_NOTIFICATION  = 30 # Days until deletion for 1st notification
SECOND_NOTIFICATION = 14 # Days until deletion for 2nd notification
THIRD_NOTIFICATION  = 7  # Days until deletion for 3rd notification

#---------------------------------------------------------------------
# Action functions
#---------------------------------------------------------------------
def action_projects():
    projects = kc.get_projects(type='demo')
    printer.output_dict({'header': 'Demo project (instances, vcpus, volumes, gb, name)'})
    count = {'size': 0, 'vcpus': 0, 'instances': 0}
    for project in projects:
        ins_data = {'count': 0, 'vcpu': 0}
        vol_data = dict({'count': 0, 'size': 0})
        for region in regions:
            nc = himutils.get_client(Nova, options, logger, region)
            cc = himutils.get_client(Cinder, options, logger, region)
            instances = nc.get_project_instances(project_id=project.id)
            ins_data = {'count': 0, 'vcpus': 0}
            for i in instances:
                ins_data['vcpus'] += i.flavor['vcpus']
                ins_data['count'] += 1
            volumes = cc.get_volumes(detailed=True, search_opts={'project_id': project.id})
            for volume in volumes:
                vol_data['size'] += volume.size
                vol_data['count'] += 1
        output = {
            '5': project.name,
            '1': ins_data['count'],
            '2': ins_data['vcpus'],
            '3': vol_data['count'],
            '4': vol_data['size']
        }
        printer.output_dict(output, one_line=True)
        count['size'] += vol_data['size']
        count['vcpus'] += ins_data['vcpus']
        count['instances'] += ins_data['count']
    printer.output_dict({
        'header': 'Count',
        'instances': count['instances'],
        'volume_gb': count['size'],
        'vcpus': count['vcpus']})

def action_instances():
    # Define pretty table
    header = [
        f"{Color.fg.MGN}{Color.bold}REGION{Color.reset}",
        f"{Color.fg.MGN}{Color.bold}PROJECT{Color.reset}",
        f"{Color.fg.MGN}{Color.bold}INSTANCE ID{Color.reset}",
        f"{Color.fg.MGN}{Color.bold}AGE{Color.reset}",
        f"{Color.fg.MGN}{Color.bold}NOTIFY 1{Color.reset}",
        f"{Color.fg.MGN}{Color.bold}NOTIFY 2{Color.reset}",
        f"{Color.fg.MGN}{Color.bold}NOTIFY 3{Color.reset}",
    ]
    table = PrettyTable()
    table._max_width = {'value' : 70}
    table.border = 0
    table.header = 1
    table.left_padding_width = 2
    table.field_names = header
    table.align[header[0]] = 'l'
    table.align[header[1]] = 'l'
    table.align[header[2]] = 'l'
    table.align[header[3]] = 'r'

    # Loop through projects
    projects = kc.get_projects(type='demo')
    with progressbar.ProgressBar(max_value=len(projects)) as progbar:
        count = 0
        for project in projects:
            count += 1
            # Ignore if project is disabled
            if not is_project_enabled(project):
                progbar.update(count)
                continue
            for region in regions:
                nc = himutils.get_client(Nova, options, logger, region)
                instances = nc.get_project_instances(project_id=project.id)
                for instance in instances:
                    created = himutils.get_date(instance.created, None, '%Y-%m-%dT%H:%M:%SZ')
                    active_days = (date.today() - created).days
                    # Get existing db entry
                    entry = db.get_first(DemoInstance,
                                         instance_id=instance.id,
                                         project_id=project.id,
                                         region=region)

                    if active_days >= MAX_AGE:
                        days = f"{Color.fg.red}{active_days}{Color.reset}"
                    elif active_days < MAX_AGE and active_days >= (MAX_AGE - FIRST_NOTIFICATION):
                        days = f"{Color.fg.ylw}{active_days}{Color.reset}"
                    else:
                        days = f"{Color.fg.grn}{active_days}{Color.reset}"

                    if entry and entry.notified1 is not None:
                        n1 = f"{Color.fg.grn}{entry.notified1.strftime('%Y-%m-%d')}{Color.reset}"
                    else:
                        n1 = f"{Color.dim}x{Color.reset}"
                    if entry and entry.notified2 is not None:
                        n2 = f"{Color.fg.grn}{entry.notified2.strftime('%Y-%m-%d')}{Color.reset}"
                    else:
                        n2 = f"{Color.dim}x{Color.reset}"
                    if entry and entry.notified3 is not None:
                        n3 = f"{Color.fg.grn}{entry.notified3.strftime('%Y-%m-%d')}{Color.reset}"
                    else:
                        n3 = f"{Color.dim}x{Color.reset}"

                    row = [
                        f"{Color.dim}{region}{Color.reset}",
                        f"{Color.fg.blu}{project.name}{Color.reset}",
                        f"{Color.dim}{instance.id}{Color.reset}",
                        days,
                        n1,
                        n2,
                        n3,
                    ]
                    table.add_row(row)
            progbar.update(count)
    table.sortby = header[0]
    print(table)

# Notify user about instance about to expire
def action_expired():
    projects = kc.get_projects(type='demo')

    # Interactive confirmation
    question = "Really send emails to users?"
    if not options.force and not options.dry_run and not himutils.confirm_action(question):
        return

    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        for project in projects:
            # Ignore if project is disabled
            if not is_project_enabled(project):
                continue
            instances = nc.get_project_instances(project_id=project.id)
            for instance in instances:
                created = himutils.get_date(instance.created, None, '%Y-%m-%dT%H:%M:%SZ')
                active_days = (date.today() - created).days
                kc.debug_log(f'{instance.id} running for {active_days} days')

                # next instance if it's not yet time for notifications
                if int(active_days) < (MAX_AGE - FIRST_NOTIFICATION):
                    continue

                # Get existing db entry, if it exists
                entry = db.get_first(DemoInstance,
                                     instance_id=instance.id,
                                     project_id=project.id,
                                     region=region)

                # Send first notification?
                if int(active_days) >= (MAX_AGE - FIRST_NOTIFICATION):
                    dbadd = add_to_db(
                        instance_id = instance.id,
                        project_id  = project.id,
                        region      = region
                    )
                    if dbadd:
                        notify_user(instance, project, region, active_days, notification_type='first')
                        continue

                # This shouldn't happen(?)
                if entry is None:
                    continue

                # Send second notification?
                if entry.notified2 is None:
                    if datetime.now() > entry.notified1 + timedelta(days=(FIRST_NOTIFICATION - SECOND_NOTIFICATION)) - timedelta(minutes=15):
                        dbupdate = update_db(
                            instance_id = instance.id,
                            project_id  = project.id,
                            region      = region,
                            notified2   = datetime.now()
                        )
                        if dbupdate:
                            notify_user(instance, project, region, active_days, notification_type='second')
                    continue

                # Send final notification?
                if entry.notified3 is None:
                    if datetime.now() > entry.notified2 + timedelta(days=(SECOND_NOTIFICATION - THIRD_NOTIFICATION)) - timedelta(minutes=15):
                        dbupdate = update_db(
                            instance_id = instance.id,
                            project_id  = project.id,
                            region      = region,
                            notified3   = datetime.now()
                        )
                        if dbupdate:
                            notify_user(instance, project, region, active_days, notification_type='final')
                    continue


# Delete instance when
#   - Z days since notification 3 was sent
# NB! We only care about when notifications were sent when deciding to delete instances
def action_delete():
    question = "Really delete expired demo instances?"
    if not options.force and not options.dry_run and not himutils.confirm_action(question):
        return

    rows = db.get_all(DemoInstance)
    for row in rows:
        if row.notified3 is None or row.notified2 is None or row.notified1 is None:
            continue
        last_notified = row.notified3
        if datetime.now() > last_notified + timedelta(days=THIRD_NOTIFICATION):
            if options.dry_run:
                p_info(f"(dry-run) [{row.region}] [project_id={row.project_id}] Would delete instance {row.instance_id}")
            else:
                nc = himutils.get_client(Nova, options, logger, row.region)
                instance = nc.get_by_id("server", row.instance_id)
                created = himutils.get_date(instance.created, None, '%Y-%m-%dT%H:%M:%SZ')
                active_days = (date.today() - created).days
                p_warning(f"[{row.region}] [project_id={row.project_id}] Deleting instance {row.instance_id}")
                nc.delete_instance(instance)
                himutils.append_to_logfile(
                    logfile,
                    datetime.now(),
                    row.region,
                    f"Deleted instance: {instance.id}",
                    f"Project ID: {row.project_id}",
                    f"Active for: {active_days} days"
                )
                p_info(f"[{row.region}] [project_id={row.project_id}] Deleting entry {row.instance_id} from database")
                db.delete(row)


# Remove entries from database that was created more than 180 days ago
def action_cleandb():
    rows = db.get_all(DemoInstance)
    for row in rows:
        created = row.created
        if datetime.now() > created + timedelta(days=180):
            if options.dry_run:
                p_info(f"(dry-run) [{row.region}] [project_id={row.project_id}] Would clean instance {row.instance_id} from DB")
            else:
                p_info(f"[{row.region}] [project_id={row.project_id}] Cleaning instance {row.instance_id} from database")
                db.delete(row)


#---------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------

# Print info message
def p_info(string):
    himutils.info(string)

# Print warning message
def p_warning(string):
    himutils.warning(string)

# Print error message
def p_error(string):
    himutils.error(string)

# Check if project is enabled
def is_project_enabled(project):
    return project.enabled

def notify_user(instance, project, region, active_days, notification_type):
    # Template to use
    template = 'notify/demo/instance_expiration.txt'

    # mail parameters
    mail = himutils.get_client(Mail, options, logger)
    mail = Mail(options.config, debug=options.debug)
    mail.set_dry_run(options.dry_run)
    fromaddr = mail.get_config('mail', 'from_addr')
    bccaddr = 'iaas-logs@usit.uio.no'
    ccaddr = None

    # Calculate the days until deletion
    enddate = {
        'first'  : FIRST_NOTIFICATION,
        'second' : SECOND_NOTIFICATION,
        'final'  : THIRD_NOTIFICATION,
    }

    mapping = {
        'project'  : project.name,
        'enddate'  : enddate[notification_type],
        'activity' : int(active_days),
        'region'   : region.upper(),
        'instance' : instance.name,
        'number'   : notification_type,
        'max_age'  : MAX_AGE,
    }
    body_content = himutils.load_template(inputfile=template,
                                          mapping=mapping,
                                          log=logger)
    msg = MIMEText(body_content, 'plain')
    msg['subject'] = f"[NREC] Your demo instance is due for deletion in {enddate[notification_type]} days"

    # Send mail to user
    if options.dry_run:
        p_info(f"Did NOT send spam to {project.admin}:")
        print(f"{Color.dim}––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––{Color.reset}")
        print(f"{Color.fg.CYN}Subject:{Color.reset} {Color.dim}{msg['subject']}{Color.reset}")
        print(f"{Color.fg.CYN}To:{Color.reset} {Color.dim}{project.admin}{Color.reset}")
        if bccaddr:
            print(f"{Color.fg.CYN}Bcc:{Color.reset} {Color.dim}{bccaddr}{Color.reset}")
        print(f"{Color.fg.CYN}From:{Color.reset} {Color.dim}{fromaddr}{Color.reset}")
        print(f"{Color.dim}---{Color.reset}")
        print(body_content)
        print(f"{Color.dim}––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––{Color.reset}")
    else:
        mail.send_mail(project.admin, msg, fromaddr, ccaddr, bccaddr)
        kc.debug_log(f'Sending mail to {project.admin} regarding {instance.id} that has been active for {active_days} days')
        himutils.append_to_logfile(
            logfile,
            datetime.now(),
            region,
            f"{notification_type} notification to: {project.admin}",
            f"Instance name: {instance.name}",
            f"Active for: {active_days} days"
        )
        p_info(f"Spam sent to {project.admin}")


# Add entry to the database if it doesn't already exists. Returns True
# if database was updated
def add_to_db(instance_id, project_id, region):
    existing_object = db.get_first(DemoInstance,
                                   instance_id=instance_id,
                                   project_id=project_id,
                                   region=region)
    if existing_object is None:
        demo_instance_entry = {
            'instance_id' : instance_id,
            'project_id'  : project_id,
            'region'      : region,
            'created'     : datetime.now(),
            'notified1'   : datetime.now(),
            'notified2'   : None,
            'notified3'   : None,
        }
        demo_instance_object = DemoInstance.create(demo_instance_entry)
        db.add(demo_instance_object)
        return True

    return False

# Update entry in the database. Returns True if database was updated
def update_db(instance_id, project_id, region, **kwargs):
    existing_object = db.get_first(DemoInstance,
                                   instance_id=instance_id,
                                   project_id=project_id,
                                   region=region)
    db.update(existing_object, kwargs)
    return True


#---------------------------------------------------------------------
# Run local function with the same name as the action (Note: - => _)
#---------------------------------------------------------------------
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.fatal(f"Function action_{options.action} not implemented")
action()
