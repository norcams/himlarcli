#!/usr/bin/env python
import sys
import time
import pprint
from himlarcli import utils as himutils
from himlarcli.foremanclient import Client
from himlarcli.parser import Parser
from himlarcli.sensu import Sensu
#from himlarcli.printer import Printer

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()


client = Client(options.config, options.debug)
region = client.get_config('openstack', 'region')
logger = client.get_logger()
sensu = Sensu(options.config, debug=options.debug)

# Load node config
node_config = himutils.load_config('config/nodes/%s.yaml' % region)
if not node_config:
    node_config = himutils.load_config('config/nodes/default.yaml')
nodes = node_config['nodes']

def action_show():
    node_name = '%s-%s' % (region, options.node)
    node = client.get_host(node_name)
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(node)

def action_list():
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

def action_install():
    node_name = '%s-%s' % (region, options.node)
    if options.node in nodes:
        client.create_node(name=node_name,
                           node_data=nodes[options.node],
                           region=region,
                           dry_run=options.dry_run)
    else:
        sys.stderr.write("Node %s not found in config/nodes/%s.yaml\n" %
                         (options.node, region))
        sys.exit(1)

def action_delete():
    node_name = '%s-%s' % (region, options.node)
    if not options.assume_yes:
        if not himutils.confirm_action('Are you sure you want to delete %s?' % node_name):
            return
    client.delete_node(node_name, options.dry_run)
    sensu.delete_client(node_name)

def action_reinstall():
    node_name = '%s-%s' % (region, options.node)
    if options.node in nodes:
        if not options.assume_yes:
            if not himutils.confirm_action('Are you sure you want to reinstall %s?' % node_name):
                return
        client.delete_node(node_name, options.dry_run)
        if options.sensu_expire:
            sensu.silence_host(node_name, options.sensu_expire)
        else:
            sensu.delete_client(node_name)
        client.create_node(name=node_name,
                           node_data=nodes[options.node],
                           region=region,
                           dry_run=options.dry_run)
    else:
        sys.stderr.write("Node %s not found in config/nodes/%s.yaml\n" %
                         (options.node, region))
        sys.exit(1)

def action_full():
    for name, node_data in sorted(nodes.iteritems()):
        node_name = '%s-%s' % (region, name)
        client.create_node(name=node_name,
                           node_data=node_data,
                           region=region,
                           dry_run=options.dry_run)
        time.sleep(10)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
