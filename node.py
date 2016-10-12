#!/usr/bin/env python
import utils
import sys
import time
import pprint
#from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
#import himlarcli.foremanclient as foreman
from himlarcli.foremanclient import Client
from himlarcli import utils as himutils

desc = 'Perform action on node (use short nodename without region or domain)'
actions = ['install', 'show', 'list', 'full']

options = utils.get_node_action_options(desc, actions, dry_run=True)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()

client = Client(options.config, options.debug, log=logger)

# Load node config
node_config = himutils.load_config('config/nodes/%s.yaml' % keystone.region)
if not node_config:
    node_config = himutils.load_config('config/nodes/default.yaml')
nodes = node_config['nodes']

if options.action[0] == 'show':
    node_name =  '%s-%s' % (keystone.region, options.node)
    node = client.get_host(node_name)
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(node)
elif options.action[0] == 'list':
    count = dict()
    print "These nodes can be intalled:"
    for name, node in sorted(nodes.iteritems()):
        if 'compute_resource' in node:
            print "node: %s (%s)" % (name, node['compute_resource'])
            if not node['compute_resource'] in count:
                count[node['compute_resource']] = 0
            count[node['compute_resource']] += 1
        else:
            print "node: %s (%s)" % (name, node['mac'])
    print "Stats:"
    print count
elif options.action[0] == 'install':
    node_name =  '%s-%s' % (keystone.region, options.node)
    if options.node in nodes:
        client.create_node(name=node_name,
                           node_data=nodes[options.node],
                           region=keystone.region,
                           dry_run=options.dry_run)
    else:
        logger.debug('=> %s not found in config/nodes/*' % options.node)
elif options.action[0] == 'full':
    for name, node_data in sorted(nodes.iteritems()):
        node_name =  '%s-%s' % (keystone.region, name)
        client.create_node(name=node_name,
                           node_data=node_data,
                           region=keystone.region,
                           dry_run=options.dry_run)
        time.sleep(10)
