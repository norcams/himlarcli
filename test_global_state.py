#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
#from himlarcli.cinder import Cinder
from himlarcli.nova import Nova
#from himlarcli.neutron import Neutron
from himlarcli.keystone import Keystone
from himlarcli.global_state import GlobalState
from himlarcli.global_state import Instance

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Region
if hasattr(options, 'region'):
        regions = kc.find_regions(region_name=options.region)
else:
        regions = kc.find_regions()

""" save a dict to database """
def action_save():
   # start db connection
   state = utils.get_client(GlobalState, options, logger)

   for region in regions:
     instance_data = {}
     instance_data['user_id'] = 'fake user id'
     instance_data['name'] = 'instance name'
     instance_data['region'] = region
     instance_data['type'] = 'test'
     instance = Instance.create(instance_data)
     state.add(instance)

   # close db connection
   state.close()

""" Purge all tables in db """
def action_purge():
    # start db connection
    state = utils.get_client(GlobalState, options, logger)

    for region in regions:
        state.purge('instance')

    # close db connection
    state.close()


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()


