#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

import re
import ipaddress
from himlarcli.keystone import Keystone
from himlarcli.neutron import Neutron
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
regions = utils.get_regions(options, kc)

def action_list():
    # pylint: disable=W0612

    blacklist, whitelist, notify = load_config()
    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        neutron = utils.get_client(Neutron, options, logger, region)
        rules = neutron.get_security_group_rules(1000)

        question = (f"Are you sure you will check {len(rules)} security group rules in {region}?")
        if not options.assume_yes and not utils.confirm_action(question):
            return

        printer.output_dict({'header': f"Rules in {region} (project, port min-max, protocol, ip)"})

        for rule in rules:
            if rule['remote_ip_prefix'] == None:
                continue

            # Only care about security groups that are being used
            sec_group = neutron.get_security_group(rule['security_group_id'])
            if not rule_in_use(sec_group, nova):
                continue

            # Get IP version ('4' or '6')
            version = ipaddress.ip_interface(rule['remote_ip_prefix']).version

            # check if project exists
            project = kc.get_by_id('project', rule['project_id'])
            if not project:
                kc.debug_log(f"could not find project {rule['project_id']}")
                continue

            # Ignore if project is disabled
            if not is_project_enabled(project):
                continue

            # Check for bogus use of /0 mask
            if str(rule['remote_ip_prefix']).endswith('/0'):
                ip = ipaddress.ip_interface(rule['remote_ip_prefix']).ip
                if ip.compressed == '0.0.0.0' or ip.compressed == '::':
                    True
                else:
                    print(f"[{region}] WARNING: Bogus /0 mask: {rule['remote_ip_prefix']} ({project.name})")
                    continue

            # check for wrong netmask
            mask = ipaddress.ip_interface(rule['remote_ip_prefix']).netmask
            packed = int(ipaddress.ip_interface(rule['remote_ip_prefix']).ip)
            if packed & int(mask) != packed:
                print(f"[{region}] WARNING: {rule['remote_ip_prefix']} has wrong netmask ({project.name})")
                continue

            # Run through whitelist
            if is_whitelist(rule, region, whitelist):
                continue

            # Run through whitelist
            if is_blacklist(rule, region, blacklist):
                continue

            # Run through notify config
            if notify_rule(rule, region, notify, project=project):
                continue

            if rule['port_range_min'] == None and rule['port_range_max'] == None:
                ports = 'ALL'
            elif rule['port_range_min'] == rule['port_range_max']:
                ports = str(rule['port_range_min'])
            else:
                ports = f"{rule['port_range_min']}-{rule['port_range_max']}"

            output = {
                '0': f"[{region}] OK: {project.name}",
                '1': ports,
                '2': rule['protocol'],
                '3': rule['remote_ip_prefix']
            }
            printer.output_dict(output, one_line=True)
            #printer.output_dict(rule)


def rule_in_use(sec_group, nova):
    instances = nova.get_project_instances(sec_group['project_id'])
    for i in instances:
        if not hasattr(i, 'security_groups'):
            continue
        for group in i.security_groups:
            if group['name'] == sec_group['name']:
                return True
    return False

def is_project_enabled(project):
    return project.enabled

def notify_rule(rule, region, notify, project=None):
    # pylint: disable=W0613
    for limit in notify['network_port_limits']:
        max_mask  = notify['network_port_limits'][limit]['max_mask']
        min_mask  = notify['network_port_limits'][limit]['min_mask']
        max_ports = notify['network_port_limits'][limit]['max_ports']
        rule_mask = int(ipaddress.ip_network(rule['remote_ip_prefix']).prefixlen)
        protocol = rule['protocol']
        if rule['port_range_max'] == None and rule['port_range_min'] == None:
            rule_ports = 65536
            #print(f"WARNING: {project.name} {rule['remote_ip_prefix']} has no ports")
            #print(rule)
        else:
            rule_ports = int(rule['port_range_max']) - int(rule['port_range_min']) + 1
        if rule_mask > max_mask or rule_mask < min_mask:
            continue
        elif rule_mask <= max_mask and rule_mask >= min_mask and rule_ports <= max_ports:
            continue
        else:
            print(f"[{region}] WARNING: {project.name} {rule['remote_ip_prefix']} {rule['port_range_min']}-{rule['port_range_max']}/{protocol} has too many open ports ({rule_ports} > {max_ports})")
            return True
    return False

def is_blacklist(rule, region, blacklist):
    # pylint: disable=W0613
    # TODO
    return False

def is_whitelist(rule, region, whitelist):
    #valid_none_check = ['remote_ip_prefix']
    for k, v in whitelist.items():
        # whitelist none empty property
        if "!None" in v and rule[k]:
            print(f"[{region}] WHITELIST: Remote group {rule['remote_group_id']}")
            return True
        # port match: both port_range_min and port_range_max need to match
        if k == 'port':
            if rule['port_range_min'] in v and rule['port_range_max'] in v:
                print(f"[{region}] WHITELIST: port {rule['port_range_min']}")
                return True
        # remote ip
        elif k == 'remote_ip_prefix':
            rule_network = ipaddress.ip_network(rule['remote_ip_prefix'])
            for r in v:
                rule_white = ipaddress.ip_network(r)
                if rule_network.version != rule_white.version:
                    continue
                if (rule_network.network_address >= rule_white.network_address and
                    rule_network.broadcast_address <= rule_white.broadcast_address):
                    print(f"[{region}] WHITELIST: {rule['remote_ip_prefix']} is part of {r}")
                    return True
        # whitelist match
        elif rule[k] in v:
            print(f"[{region}] WHITELIST: Exact match: {rule[k]}")
            return True
    return False

def load_config():
    config_files = {
        'blacklist': 'config/security_group/blacklist.yaml',
        'whitelist': 'config/security_group/whitelist.yaml',
        'notify': 'config/security_group/notify.yaml'}
    config = dict()
    for file_type, config_file in config_files.items():
        config[file_type] = utils.load_config(config_file)
        kc.debug_log('{}: {}'.format(file_type, config[file_type]))
    return [(v) for v in config.values()]


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
