#!/usr/bin/env python

""" Test if we have access to service net """

import os
import sys
import logging
import ConfigParser
from himlarcli import utils
import utils as cli

options = cli.get_options('Test access to service net', hosts=False, debug=False)
config = utils.get_config(options.config)

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

net = config._sections['openstack']['has_trp']
if net == 1:
    print "Result: SUCCESS!"
else:
    print "Result: NO ACCESS!"
