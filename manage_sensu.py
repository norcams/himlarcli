#!/usr/bin/env python
from himlarcli.parser import Parser
from himlarcli.sensu import Sensu
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
sensu = Sensu(options.config, debug=options.debug)
sensu.set_dry_run(options.dry_run)
host = options.host

def action_list_silenced():
    sensu.list_silenced()

def action_unsilence():
    sensu.clear_silenced(host)

def action_silence():
    expire = options.expire
    sensu.silence_host(host, expire)

def action_delete():
    sensu.delete_client(host)

action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
