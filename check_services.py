#!/usr/bin/env python
import utils
import http.client
import statsd
from himlarcli import utils as himutils
import socket

desc = 'Do a remote check of web services'
options = utils.get_options(desc, hosts=False, debug=True)

# Himmlar config
config = himutils.get_config(options.config)
region = config.get('openstack', 'region')
logger = himutils.get_logger(__name__, config, options.debug)

# statsd
statsd_server = config.get('statsd', 'server')
statsd_port = config.get('statsd', 'port')
prefix = config.get('statsd', 'prefix')
statsd = statsd.StatsClient(statsd_server, statsd_port, prefix=f'{prefix}.{region}.check')

# Services to check
services = himutils.load_region_config('config/checks', region=region, log=logger)

for name, check in sorted(services['checks'].items()):
    if 'timeout' in check:
        timeout = check['timeout']
    else:
        timeout = 10
    if check['ssl']:
        c = http.client.HTTPSConnection(check['host'], timeout=timeout)
    else:
        c = http.client.HTTPConnection(check['host'], timeout=timeout)
    try:
        c.request("HEAD", check['url'])
        response = c.getresponse()
        status = response.status
    except socket.error as e:
        logger.debug("=> error on connect: %s" % e)
        status = 0
    statsd.gauge(name, status)
    if status in check['code']:
        statsd.gauge(name, 1)
        print('%s -> ok' % check['host'])
    else:
        statsd.gauge(name, 0)
        logger.debug('=> %s = %s' % (name, status))
        print('%s -> failed' % check['host'])
