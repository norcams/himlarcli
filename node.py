#!/usr/bin/env python
import utils
import sys
#from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
#import himlarcli.foremanclient as foreman
from himlarcli.foremanclient import Client
from himlarcli import utils as himutils

desc = 'Setup compute resources and profiles'
options = utils.get_options(desc, hosts=False, dry_run=True)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()

client = Client(options.config, options.debug, log=logger)
foreman = client.get_client()

# Load first region config
node_config = himutils.load_config('config/nodes/%s.yaml' % keystone.region)
if not node_config:
    node_config = himutils.load_config('config/nodes/default.yaml')
nodes = node_config['nodes']

# Available compute resources
resources = foreman.index_computeresources()
found_resources = dict({})
for r in resources['results']:
    found_resources[r['name']] = r['id']

def get_node_data(var, node_data, default=None):
    if var in node_data:
        return node_data[var]
    else:
        return default

# Crate nodes
for name, node_data in nodes.iteritems():
    host = dict()
    host['name'] = '%s-%s' % (keystone.region, name)
    if client.get_host(host['name']):
        logger.debug('=> node %s found' % host['name'])
        continue
    host['build'] = get_node_data('build', node_data, '1')
    host['hostgroup_id'] = get_node_data('hostgroup', node_data, '1')
    host['compute_profile_id'] = get_node_data('compute_profile', node_data, '1')

    if 'mac' in node_data:
        host['mac'] = node_data['mac']
    if 'compute_resource' in node_data:
        compute_resource = '%s-%s' % (keystone.region, node_data['compute_resource'])
        if compute_resource in found_resources:
            host['compute_resource_id'] = found_resources[compute_resource]
        else:
            logger.debug('=> compute resource %s not found' % compute_resource)
    elif 'mac' not in node_data:
        logger.critical('=> mac or compute resource are mandatory for %s' % name)
        continue
    else:
        host['compute_resource_id'] = 'nil'
    if not options.dry_run:
        logger.debug('=> create host %s' % host)
        foreman.create_hosts(host)
    else:
        print host
