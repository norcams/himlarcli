#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.sensugo import SensuGo
from himlarcli.foremanclient import ForemanClient
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils

parser = Parser()
parser.toggle_show('dry-run')
options = parser.parse_args()
printer = Printer(options.format)

sensu = SensuGo(options.config, options.debug)

foreman = ForemanClient(options.config, options.debug)
foreman.set_per_page(500)
logger = foreman.get_logger()

def action_hosts():
    hostlist_sensu = []
    sensu_hosts = sensu.get_client().entities.list()
    for host in sensu_hosts:
        hostlist_sensu.append(host.name)

    hostlist_foreman = []
    foreman_hosts = foreman.get_hosts('*')
    if foreman_hosts['results']:
        for host in foreman_hosts['results']:
            hostname = host['name'].split('.')[0]
            hostlist_foreman.append(hostname)

    diff_foreman_minus_sensu = list(set(hostlist_foreman) - set(hostlist_sensu))
    diff_sensu_minus_foreman = list(set(hostlist_sensu) - set(hostlist_foreman))
    printer.output_dict({'not_in_sensu': diff_foreman_minus_sensu})
    printer.output_dict({'not_in_foreman': diff_sensu_minus_foreman})


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
