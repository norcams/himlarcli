#!/usr/bin/env python
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.sensugo import SensuGo
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)
#sensu = Sensu(options.config, debug=options.debug)
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
    for check in silenced:
        print(check.name)

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
    print('not working!')
    #sensu.delete_client(options.host)

action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
