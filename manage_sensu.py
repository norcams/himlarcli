#!/usr/bin/env python
from himlarcli.parser import Parser
from himlarcli.sensu import Sensu
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
sensu = Sensu(options.config, debug=options.debug)

def action_list_silenced():
    sensu.list_silenced()

def action_unsilence():
    sensu.clear_silenced(options.host)

def action_silence():
    sensu.silence_host(options.host, options.expire, options.reason)

def action_delete():
    sensu.delete_client(options.host)

action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
