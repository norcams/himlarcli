#!/usr/bin/env python
import utils
from himlarcli.keystone import Keystone
from himlarcli               .foremanclient import ForemanClient
from himlarcli                import utils as himutils

# Fix foreman                functions and logger not-callable
# pylint: disa               ble=E1101,E1102

desc = 'Setup                Foreman for himlar'
options = utils.get_options(desc, hosts=False)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()
domain = keystone.get_config('openstack', 'domain')

foreman = ForemanClient(options.config, options.debug, log=logger)
client = foreman.get_client()

config = himutils.load_config('config/foreman/default.yaml')

foreman.create_or_update_resource('media', config['media']['name'], config['media'])
