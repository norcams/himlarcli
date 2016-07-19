#!/usr/bin/env python
import utils
import sys
import ConfigParser
from himlarcli.foremanclient import Client

desc = 'Create an ansible inventory hostfile in ./hostfile.<loc>'
options = utils.get_options(desc, hosts=False)

foreman = Client(options.config, options.debug)

hosts = foreman.get_hosts('*')
hostlist = dict()
for host in hosts['results']:
  hostname = host['name'].split('.')[0]
  loc,role,id = hostname.split('-')
  group = "%s-%s" % (loc, role)
  if not group in hostlist:
    hostlist[group] = []
  hostlist[group].append(hostname)

children = "%s:children" % loc
filename = "hostfile.%s" % loc
nodes = "%s-nodes:children" % loc
physical = { 'storage', 'compute', 'controller' }

parser = ConfigParser.ConfigParser(allow_no_value=True)
parser.add_section(children)
parser.add_section(nodes)

for section,hosts in hostlist.iteritems():
  loc, role = sectin.split('-')
  parser.set(children, section)
  parser.add_section(section)
  if role not in physical:
    parser.set(nodes, section)
  for host in hosts:
    parser.set(section, host)

with open(filename, 'w') as f:
      parser.write(f)
