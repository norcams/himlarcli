#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

import re
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
        question = ("Are you sure you will check {} security group rules in {}?"
                    .format(len(rules), region))
        if not options.assume_yes and not utils.confirm_action(question):
            return
        printer.output_dict({'header': 'Rules in {} (project, port, ip)'
                                       .format(region)})
        for rule in rules:
            if is_whitelist(rule, whitelist):
                continue
            if is_blacklist(rule, blacklist):
                continue
            sec_group = neutron.get_security_group(rule['security_group_id'])
            if not rule_in_use(sec_group, nova):
                continue
            # check if project exists
            project = kc.get_by_id('project', rule['project_id'])
            if not project:
                kc.debug_log('could not find project {}'.
                             format(rule['project_id']))
                continue
            output = {
                '0': project.name,
                '1': "{}-{}".format(rule['port_range_min'], rule['port_range_max']),
                '2': rule['remote_ip_prefix']
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

def notify_rule(rule, notify):
    # pylint: disable=W0613
    # TODO
    return False

def is_blacklist(rule, blacklist):
    # pylint: disable=W0613
    # TODO
    return False

def is_whitelist(rule, whitelist):
    #valid_none_check = ['remote_ip_prefix']
    for k, v in whitelist.iteritems():
        # whitelist none empty property
        if "!None" in v and rule[k]:
            return True
        # port match: both port_range_min and port_range_max need to match
        if k == 'port':
            if rule['port_range_min'] in v and rule['port_range_max'] in v:
                return True
        # regex remote ip
        elif k == 'remote_ip_prefix_regex':
            for regex in v:
                pattern = re.compile("^{}$".format(regex))
                if pattern.search(rule['remote_ip_prefix']):
                    return True
        # whitelist match
        elif rule[k] in v:
            return True
    return False


def load_config():
    config_files = {
        'blacklist': 'config/security_group/blacklist.yaml',
        'whitelist': 'config/security_group/whitelist.yaml',
        'notify': 'config/security_group/notify.yaml'}
    config = dict()
    for file_type, config_file in config_files.iteritems():
        config[file_type] = utils.load_config(config_file)
        kc.debug_log('{}: {}'.format(file_type, config[file_type]))
    return [(v) for v in config.itervalues()]

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
