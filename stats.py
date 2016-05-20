#!/usr/bin/env python

import pprint
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone


keystoneclient = Keystone('config.ini')
projects_count = keystoneclient.get_project_count('dataporten')

novaclient = Nova('config.ini')
novastats = novaclient.get_stats('dataporten')

stats = dict()
stats['projects'] = {}
stats['instances'] = {}
stats['projects']['count'] = projects_count
stats['instances']['count'] = novastats['count']

pp = pprint.PrettyPrinter(indent=2)
pp.pprint(stats)
