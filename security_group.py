#!/usr/bin/env python

import ipaddress
from datetime import datetime
from datetime import timedelta
from email.mime.text import MIMEText

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.neutron import Neutron
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli import utils as himutils
from himlarcli.global_state import GlobalState, SecGroupRule

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
regions = himutils.get_regions(options, kc)

# Initialize database connection
db = himutils.get_client(GlobalState, options, logger)

# Use to (de)activate checks
ENABLE_BOGUS_0_MASK = True
ENABLE_WRONG_MASK   = False
ENABLE_PORT_LIMIT   = False

#---------------------------------------------------------------------
# Action functions
#---------------------------------------------------------------------
def action_list():
    for region in regions:
        neutron = himutils.get_client(Neutron, options, logger, region)
        rules   = neutron.get_security_group_rules(1000)

        question = f"Are you sure you will list {len(rules)} security group rules in {region}?"
        if not options.assume_yes and not himutils.confirm_action(question):
            return

        printer.output_dict({'header': f"Rules in {region} (project, ports, protocol, cidr)"})
        for rule in rules:
            # check if project exists
            project = kc.get_by_id('project', rule['project_id'])
            if not project:
                kc.debug_log(f"could not find project {rule['project_id']}")
                continue

            if is_whitelist(rule, project, region):
                continue
            if is_blacklist(rule, project, region):
                continue

            output = {
                '0': project.name,
                '1': f"{rule['port_range_min']}-{rule['port_range_max']}",
                '2': rule['protocol'],
                '3': rule['remote_ip_prefix']
            }
            printer.output_dict(output, one_line=True)


def action_check():
    for region in regions:
        nova    = himutils.get_client(Nova, options, logger, region)
        neutron = himutils.get_client(Neutron, options, logger, region)
        rules   = neutron.get_security_group_rules(1000)

        question = f"Are you sure you will check {len(rules)} security group rules in {region}?"
        if not options.assume_yes and not himutils.confirm_action(question):
            return

        count = {
            'total'         : 0,  # Total number of rules checked
            'whitelist'     : 0,  # Number of whitelisted rules
            'unused'        : 0,  # Number of rules not used on instances
            'proj_disabled' : 0,  # Number of rules for disabled projects
            'wrong_mask'    : 0,  # Number of rules with wrong netmask
            'bogus_0_mask'  : 0,  # Number of rules with bogus /0 mask
            'port_limit'    : 0,  # Number of rules exceeding port limits
            'orphan'        : 0,  # Rules not belonging to a project
            'ok'            : 0,  # Number of rules deemed OK
        }
        for rule in rules:
            count['total'] += 1

            # Sometimes the remote IP prefix is empty or None. If that
            # happens, rewrite to '0.0.0.0/0' or '::/0' for IPv4 and
            # IPv6, respectively
            if rule['remote_ip_prefix'] is None:
                if rule['ethertype'] == 'IPv4':
                    rule['remote_ip_prefix'] = '0.0.0.0/0'
                else:
                    rule['remote_ip_prefix'] = '::/0'

            # Check if rule owner and security group owner is same
            if check_wrong_rule_owner(rule, neutron, region):
                continue

            # check if project exists
            project = kc.get_by_id('project', rule['project_id'])
            if not project:
                count['orphan'] += 1
                kc.debug_log(f"could not find project {rule['project_id']}")
                continue

            # Ignore if project is disabled
            if not is_project_enabled(project):
                count['proj_disabled'] += 1
                continue

            # Check for bogus use of /0 mask
            if ENABLE_BOGUS_0_MASK:
                bogus_0_mask = check_bogus_0_mask(rule, region, project, neutron, nova)
                if bogus_0_mask == "yes":
                    count['bogus_0_mask'] += 1
                    continue
                if bogus_0_mask == "not-in-use":
                    count['unused'] += 1
                    continue

            # check for wrong netmask
            if ENABLE_WRONG_MASK:
                wrong_mask = check_wrong_mask(rule, region, project, neutron, nova)
                if wrong_mask == "yes":
                    count['wrong_mask'] += 1
                    continue
                if wrong_mask == "not-in-use":
                    count['unused'] += 1
                    continue

            # Run through whitelist
            if is_whitelist(rule, project, region):
                count['whitelist'] += 1
                continue

            # Run through blacklist
            if is_blacklist(rule, project, region):
                continue

            # Check port limits
            if ENABLE_PORT_LIMIT:
                port_limits = check_port_limits(rule, region, project, neutron, nova)
                if port_limits == "yes":
                    count['port_limit'] += 1
                    continue
                if port_limits == "not-in-use":
                    count['unused'] += 1
                    continue

            if rule['port_range_min'] is None and rule['port_range_max'] is None:
                ports = 'ALL'
            elif rule['port_range_min'] == rule['port_range_max']:
                ports = str(rule['port_range_min'])
            else:
                ports = f"{rule['port_range_min']}-{rule['port_range_max']}"

            verbose_info(f"[{region}] [{project.name}] OK: " +
                         f"ports {ports}/{rule['protocol']} " +
                         f"to {rule['remote_ip_prefix']}")
            count['ok'] += 1

        # Write a summary for the region
        if not options.notify:
            num_ok = count['ok'] + count['unused'] + count['proj_disabled'] + count['whitelist']
            num_problems = count['bogus_0_mask'] + count['wrong_mask'] + count['port_limit']
            print()
            print(f"Summary for region {region}:")
            print("====================================================")
            print(f"  OK ({num_ok}):")
            print(f"    OK rules . . . . . . . . . : {count['ok']}")
            print(f"    Disabled projects. . . . . : {count['proj_disabled']}")
            print(f"    Whitelisted rules. . . . . : {count['whitelist']}")
            print(f"    Unused rules . . . . . . . : {count['unused']}")
            print(f"  PROBLEMS ({num_problems}):")
            print(f"    Bogus /0 mask. . . . . . . : {count['bogus_0_mask']}")
            print(f"    Wrong mask . . . . . . . . : {count['wrong_mask']}")
            print(f"    Port limits exceeded . . . : {count['port_limit']}")
            print(f"    Orphans. . . . . . . . . . : {count['orphan']}")
            print()
            print(f"  TOTAL rules checked in {region}: {count['total']}")


def action_clean():
    age_limit = general['clean_dbentry_days']
    rows = db.get_all(SecGroupRule)
    for row in rows:
        last_notified = row.notified
        if datetime.now() > last_notified + timedelta(days=age_limit):
            verbose_info(f"Deleting rule {row.rule_id} from database")
            db.delete(row)

#---------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------
def notify_user(rule, region, project, violation_type, minimum_netmask=None, real_ip=None):
    neutron = himutils.get_client(Neutron, options, logger, region)

    # Templates
    template = {
        'bogus_0_mask' : 'notify/secgroup_bogus_0_mask.txt',
        'wrong_mask'   : 'notify/secgroup_wrong_mask.txt',
        'port_limit'   : 'notify/secgroup_port_limit.txt',
    }

    # Project info
    project_admin = project.admin if hasattr(project, 'admin') else 'None'
    project_contact = project.contact if hasattr(project, 'contact') else 'None'

    # Security group info
    secgroup = neutron.get_security_group(rule['security_group_id'])

    # Set common mail parameters
    mail = himutils.get_client(Mail, options, logger)
    mail = Mail(options.config, debug=options.debug)
    mail.set_dry_run(options.dry_run)
    fromaddr = general['mail_from_address']
    bccaddr =  general['mail_bcc_address']
    if project_contact != 'None':
        ccaddr = project_contact
    else:
        ccaddr = None

    # Construct mail content
    if rule['ethertype'] == 'IPv4':
        ip_family_0 = '0.0.0.0'
    else:
        ip_family_0 = '::'
    mapping = {
        'project_name'          : project.name,
        'project_id'            : project.id,
        'secgroup_name'         : secgroup['name'],
        'secgroup_id'           : secgroup['id'],
        'rule_id'               : rule['id'],
        'rule_ethertype'        : rule['ethertype'],
        'rule_protocol'         : rule['protocol'],
        'rule_ports'            : f"{rule['port_range_min']}-{rule['port_range_max']}",
        'rule_remote_ip_prefix' : rule['remote_ip_prefix'],
        'rule_ipaddr'           : rule['remote_ip_prefix'].split('/', 1)[0],
        'rule_netmask'          : rule['remote_ip_prefix'].split('/', 1)[1],
        'region'                : region,
        'minimum_netmask'       : minimum_netmask,
        'real_ip'               : real_ip,
        'ip_family_0'           : ip_family_0,
        'notification_interval' : general['notification_interval_days'],
    }
    body_content = himutils.load_template(inputfile=template[violation_type],
                                          mapping=mapping,
                                          log=logger)
    msg = MIMEText(body_content, 'plain')
    msg['subject'] = f"NREC: Problematic security group rule found in project {project.name}"

    # Send mail to user
    mail.send_mail(project_admin, msg, fromaddr, ccaddr, bccaddr)
    if options.dry_run:
        print(f"Did NOT send spam to {project_admin}")
        print(f"Subject: {msg['subject']}")
        print(f"To: {project_admin}")
        if ccaddr:
            print(f"Cc: {ccaddr}")
        if bccaddr:
            print(f"Bcc: {bccaddr}")
        print(f"From: {fromaddr}")
        print('---')
        print(body_content)
    else:
        print(f"Spam sent to {project_admin}")

# Add entry to the database if it doesn't already exists, or update
# the entry if it is older than X days.  Returns True if database was
# updated
def add_or_update_db(rule_id, secgroup_id, project_id, region):
    limit = general['notification_interval_days']
    existing_object = db.get_first(SecGroupRule,
                                   rule_id=rule_id,
                                   secgroup_id=secgroup_id,
                                   project_id=project_id,
                                   region=region)
    if existing_object is None:
        rule_entry = {
            'rule_id'     : rule_id,
            'secgroup_id' : secgroup_id,
            'project_id'  : project_id,
            'region'      : region,
            'notified'    : datetime.now(),
            'created'     : datetime.now(),
        }
        rule_object = SecGroupRule.create(rule_entry)
        db.add(rule_object)
        return True

    last_notified = existing_object.notified
    if datetime.now() > last_notified + timedelta(days=limit):
        verbose_warning(f"[{region}] More than {limit} days since {rule_id} was notified")
        rule_diff = { 'notified': datetime.now() }
        db.update(existing_object, rule_diff)
        return True

    return False

# Check for wrong use of mask 0. Returns true if the mask is 0 and the
# IP is not one of "0.0.0.0" or "::"
def check_bogus_0_mask(rule, region, project, neutron, nova):
    ip = ipaddress.ip_interface(rule['remote_ip_prefix']).ip
    if str(rule['remote_ip_prefix']).endswith('/0') and ip.compressed not in ('0.0.0.0', '::'):
        if not rule_in_use(rule, neutron, nova):
            return "not-in-use"
        min_mask = calculate_minimum_netmask(ip, rule['ethertype'])
        verbose_error(f"[{region}] [{project.name}] " +
                      f"{rule['remote_ip_prefix']} has bogus /0 subnet mask " +
                      f"(minimum mask: {min_mask})")
        if options.notify:
            do_notify = add_or_update_db(
                rule_id     = rule['id'],
                secgroup_id = rule['security_group_id'],
                project_id  = rule['project_id'],
                region      = region
            )
            if do_notify:
                notify_user(rule, region, project,
                            violation_type='bogus_0_mask',
                            minimum_netmask=min_mask)
        return "yes"
    return "no"

# Check if the netmask is wrong for the IP
def check_wrong_mask(rule, region, project, neutron, nova):
    mask   = ipaddress.ip_interface(rule['remote_ip_prefix']).netmask
    ip     = ipaddress.ip_interface(rule['remote_ip_prefix']).ip
    packed = int(ip)
    if packed & int(mask) != packed:
        if not rule_in_use(rule, neutron, nova):
            return "not-in-use"
        min_mask = calculate_minimum_netmask(ip, rule['ethertype'])
        real_ip = real_ip_for_netmask(ip, mask)
        verbose_error(f"[{region}] [{project.name}] " +
                      f"{rule['remote_ip_prefix']} has wrong subnet mask " +
                      f"(minimum mask: {min_mask})")
        if options.notify:
            do_notify = add_or_update_db(
                rule_id     = rule['id'],
                secgroup_id = rule['security_group_id'],
                project_id  = rule['project_id'],
                region      = region
            )
            if do_notify:
                notify_user(rule, region, project,
                            violation_type='wrong_mask',
                            minimum_netmask=min_mask,
                            real_ip=real_ip)
        return "yes"
    return "no"

# Calculates minimum netmask for a given IP
def calculate_minimum_netmask(ip, family):
    if family == "IPv6":
        maxmask = 128
    elif family == "IPv4":
        maxmask = 32
    packed = int(ip)
    for i in range(maxmask,0,-1):
        mask = ipaddress.ip_interface(f'{ip}/{i}').netmask
        if packed & int(mask) != packed:
            return i+1
    return 0

# Calculates the real IP address after applying the netmask
def real_ip_for_netmask(ip, mask):
    packed = int(ip)
    real_ip = packed & int(mask)
    return str(ipaddress.ip_address(real_ip))

# Check if security group rule is in use
def rule_in_use(rule, neutron, nova):
    sec_group = neutron.get_security_group(rule['security_group_id'])
    instances = nova.get_project_instances(sec_group['project_id'])
    for i in instances:
        if not hasattr(i, 'security_groups'):
            continue
        for group in i.security_groups:
            if group['name'] == sec_group['name']:
                return True
    return False

# Check if project is enabled
def is_project_enabled(project):
    return project.enabled

# Check for port limit violation
def check_port_limits(rule, region, project, neutron, nova):
    protocol = rule['protocol']
    rule_mask = int(ipaddress.ip_network(rule['remote_ip_prefix']).prefixlen)
    if rule_mask in notify['netmask_port_limits'][rule['ethertype']]:
        max_ports = notify['netmask_port_limits'][rule['ethertype']][rule_mask]
    else:
        max_ports = notify['netmask_port_limits'][rule['ethertype']]['default']
    if rule['port_range_max'] is None and rule['port_range_min'] is None:
        rule_ports = 65536
    else:
        rule_ports = int(rule['port_range_max']) - int(rule['port_range_min']) + 1
    if rule_ports > max_ports:
        if not rule_in_use(rule, neutron, nova):
            return "not-in-use"
        verbose_warning(f"[{region}] [{project.name}] {rule['remote_ip_prefix']} " +
                        f"{rule['port_range_min']}-{rule['port_range_max']}/{protocol} " +
                        f"has too many open ports ({rule_ports} > {max_ports})")
        if options.notify:
            do_notify = add_or_update_db(
                rule_id     = rule['id'],
                secgroup_id = rule['security_group_id'],
                project_id  = rule['project_id'],
                region      = region
            )
            if do_notify:
                notify_user(rule, region, project,
                            violation_type='port_limit')
        return "yes"
    return "no"

# Blacklisting is currently not implemented
def is_blacklist(rule, project, region):
    return False

# Print verbose info
def verbose_info(string):
    if options.verbose >= 3:
        himutils.info(string)

# Print verbose warning
def verbose_warning(string):
    if options.verbose >= 2:
        himutils.warning(string)

# Print verbose error
def verbose_error(string):
    if options.verbose >= 1:
        himutils.error(string)

# Check if rule is whitelisted
def is_whitelist(rule, project, region):
    # Whitelist entire projects across regions
    if project.name in whitelist['project_name']:
        verbose_info(f"[{region}] [{project.name}] WHITELIST " +
                     f"project: {rule['project_id']}")
        return True
    # Whitelist rule ID in region
    if rule['id'] in whitelist['region'][region]['rule_id']:
        verbose_info(f"[{region}] [{project.name}] WHITELIST " +
                     f"rule ID: {rule['id']}")
        return True
    # Whitelist security group ID in region
    if rule['security_group_id'] in whitelist['region'][region]['secgroup_id']:
        verbose_info(f"[{region}] [{project.name}] WHITELIST " +
                     f"security group ID: {rule['security_group_id']}")
        return True
    # Regular whitelists
    for key,value in whitelist.items():
        if key == 'region' or key == 'project_name':
            continue
        # whitelist none empty property
        if "!None" in value and rule[key]:
            verbose_info(f"[{region}] [{project.name}] WHITELIST " +
                         f"{key}: not empty")
            return True
        # single port match: both port_range_min and port_range_max need to match
        elif key == 'port':
            if rule['port_range_min'] in value and rule['port_range_max'] in value:
                verbose_info(f"[{region}] [{project.name}] WHITELIST " +
                             f"port: {rule['port_range_min']}")
                return True
        # remote ip
        elif key == 'remote_ip_prefix':
            try:
                rule_network = ipaddress.ip_network(rule['remote_ip_prefix'])
            except ValueError:
                return False
            for r in value:
                rule_white = ipaddress.ip_network(r)
                if rule_network.version != rule_white.version:
                    continue
                # NOTE: If python is 3.7 or newer, replace with subnet_of()
                if (rule_network.network_address >= rule_white.network_address and
                    rule_network.broadcast_address <= rule_white.broadcast_address):
                    verbose_info(f"[{region}] [{project.name}] WHITELIST " +
                                 f"remote cidr: {rule['remote_ip_prefix']} " +
                                 f"is part of {r}")
                    return True
        # whitelist match
        elif rule[key] in value:
            verbose_info(f"[{region}] [{project.name}] WHITELIST {key}: {rule[key]}")
            return True
    return False

# Check if the owner of the security group is the same as the owner of
# the security group rule
def check_wrong_rule_owner(rule, neutron, region):
    sec_group = neutron.get_security_group(rule['security_group_id'])
    if rule['project_id'] != sec_group['project_id']:
        verbose_error(f"[{region}] Mismatch for rule ID={rule['id']}: " +
                      f"Security group project {sec_group['project_id']} " +
                      f"!= Rule project {rule['project_id']}")
        return True
    return False

# Load config
def load_config():
    config_files = {
        'blacklist': 'config/security_group/blacklist.yaml',
        'whitelist': 'config/security_group/whitelist.yaml',
        'notify':    'config/security_group/notify.yaml',
        'general':   'config/security_group/general.yaml',
    }
    config = {}
    for file_type, config_file in config_files.items():
        config[file_type] = himutils.load_config(config_file)
        kc.debug_log(f"{file_type}: {config[file_type]}")
    return [(v) for v in config.values()]


#---------------------------------------------------------------------
# Run local function with the same name as the action (Note: - => _)
#---------------------------------------------------------------------
blacklist, whitelist, notify, general = load_config()
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.fatal(f"Function action_{options.action} not implemented")
action()
