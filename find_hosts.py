#!/usr/bin/env python
import utils
import sys
import pprint
import yaml
import ConfigParser
from himlarcli.foremanclient import Client
from himlarcli import utils as himutils

desc = 'Create an inventory config in ./config.<loc>'
options = utils.get_options(desc, hosts=False)

foreman = Client(options.config, options.debug)

hosts = foreman.get_hosts('*')
hostlist = dict({'nodes': {}})
for host in hosts['results']:
    hostname = str(host['name']).split('.')[0]
    loc,role,id = hostname.split('-')
    node = "%s-%s" % (role, id)
    host['name'].split('.')[0]
    if not host['managed']:
        continue
    if not host['compute_resource_name']:
        hostlist['nodes'][node] = dict()
        hostlist['nodes'][node]['mac'] = str(host['mac'])
    else:
        hostlist['nodes'][node] = dict()
        hostlist['nodes'][node]['compute_resource'] = 'controller-01'
        hostlist['nodes'][node]['compute_profile'] = 1
    #pp = pprint.PrettyPrinter(indent=2)
    #pp.pprint(host)

with open('%s.yaml' % loc, 'w') as outfile:
    yaml.dump(hostlist, outfile, default_flow_style=False)
