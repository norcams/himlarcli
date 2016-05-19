#!/usr/bin/python
import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone

options = utils.get_host_options('Print users on nova compute host', hosts=1)
novaclient = Nova(options.config, options.host[0])
print novaclient.list_users()
