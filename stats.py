#!/usr/bin/env python

import pprint
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone

options = utils.get_options('Print openstack location stats', hosts=False)

keystoneclient = Keystone(options.config, options.debug)
projects_count = keystoneclient.get_project_count('dataporten')

novaclient = Nova(options.config, debug=options.debug)
novastats = novaclient.get_stats('dataporten')

stats = dict()
stats['projects'] = {}
stats['instances'] = {}
stats['projects']['count'] = projects_count
stats['instances']['count'] = novastats['count']

pp = pprint.PrettyPrinter(indent=2)
pp.pprint(stats)
