#!/usr/bin/env python

import sys
import pprint
import utils
import statsd
from himlarcli import utils as himutils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone

options = utils.get_options('Print openstack location stats', hosts=False)

# Project
keystoneclient = Keystone(options.config, options.debug)
projects_count = keystoneclient.get_project_count('dataporten')
users_count = keystoneclient.get_user_count('dataporten')
logger = keystoneclient.get_logger()

stats = dict()
stats['projects'] = {}
stats['instances'] = {}
stats['users'] = {}
stats['projects'][keystoneclient.region] = {}
stats['projects'][keystoneclient.region]['count'] = projects_count
stats['users'][keystoneclient.region] = {}
stats['users'][keystoneclient.region]['count'] = users_count

server = keystoneclient.get_config('statsd', 'server')
port = keystoneclient.get_config('statsd', 'port')

# Regions
regions = himutils.load_region_config('config/stats',
                                      region=keystoneclient.region,
                                      log=logger)

# Instances
for name, info in sorted(regions['regions'].iteritems()):
    logger.debug('=> count region %s' % name)
    novaclient = Nova(options.config, debug=options.debug, region=name)
    novastats = novaclient.get_stats()
    stats['instances'][name] = {}
    stats['instances'][name]['count'] = novastats['count']

prefix = 'uh-iaas'
c = statsd.StatsClient(server, port, prefix=prefix)
for t, s in stats.iteritems():
    for r, d in s.iteritems():
        name = '%s.%s' % (r, t)
        count = d['count']
        print '%s = %s' % (name, count)
        c.gauge(name, count)
