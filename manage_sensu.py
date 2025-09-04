#!/usr/bin/env python
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.sensugo import SensuGo
from himlarcli import utils as utils

utils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)
sensu = SensuGo(options.config, options.debug)

def action_events():
    sensu_events = sensu.get_events()
    printer.output_dict({'header': 'Event list (is_silenced, state, check)'})
    for event in sensu_events:
        if event.spec['check']['status'] > 0:
            out_event = {
                '1': event.spec['check']['is_silenced'],
                '2': event.spec['check']['state'],
                '3': event.name,
#                '4': event.spec['check']['output']
            }
            printer.output_dict(out_event, sort=True, one_line=True)

def action_list_silenced():
    silenced = sensu.list_silenced()
    printer.output_dict({'header': 'Silenced checks (name, reason)'})
    for check in silenced:
        if 'reason' in check.spec:
            reason = '=> ' + check.spec['reason']
        else:
            reason = '=> unknown'
        out_event = {
            '1': check.name,
            '2': reason
        }
        printer.output_dict(out_event, sort=True, one_line=True)

def action_show_silenced():
    silenced = sensu.get_silenced(options.host, options.check)
    printer.output_dict(silenced.spec)

def action_unsilence():
    print(f'unsilence entity:{options.host}:{options.check}')
    sensu.clear_silenced(options.host, options.check)

def action_silence():
    print(f'silence entity:{options.host}:{options.check}')
    sensu.silence_check(options.host, options.check, options.expire, options.reason)

def action_delete():
    sensu.delete_client(options.host)

action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error(f"Function action_{options.action}() not implemented")
action()
