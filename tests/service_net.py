#!/usr/bin/env python

""" Test if we have access to service net """

import os
import sys
import logging
import ConfigParser
from himlarcli import utils
import utils as cli

options = cli.get_options('Test access to service net', hosts=False, debug=False)
config_path = options.config

if not os.path.isfile(config_path):
    logging.critical("Could not find config file: %s" %config_path)
    sys.exit(1)
config = ConfigParser.ConfigParser()
config.read(config_path)

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

net = config._sections['openstack']['service_net']
if utils.has_network_access(net, logging):
    print "Result: SUCCESS!"
else:
    print "Result: NO ACCESS!"
