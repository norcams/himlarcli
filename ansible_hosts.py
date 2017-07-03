#!/usr/bin/env python
import utils
import ConfigParser
from himlarcli.foremanclient import Client

desc = 'Create an ansible inventory hostfile in ./hostfile.<loc>'
options = utils.get_options(desc, hosts=False)

foreman = Client(options.config, options.debug)

hosts = foreman.get_hosts('*')
hostlist = dict()
for host in hosts['results']:
    hostname = host['name'].split('.')[0]
    loc, role, num = hostname.split('-')
    group = "%s-%s" % (loc, role)
    if not group in hostlist:
        hostlist[group] = []
    hostlist[group].append(hostname)

children = "%s:children" % loc
filename = "hostfile.%s" % loc
nodes = "%s-nodes:children" % loc
exclude_nodes = {'storage', 'compute', 'controller', 'leaf', 'login', 'nat'}

parser = ConfigParser.ConfigParser(allow_no_value=True)
parser.add_section(children)
parser.add_section(nodes)

for section, hosts in sorted(hostlist.iteritems()):
    loc, role = section.split('-')
    parser.set(children, section)
    parser.add_section(section)
    if role not in exclude_nodes:
        parser.set(nodes, section)
    for host in hosts:
        parser.set(section, host)

with open(filename, 'w') as f:
    parser.write(f)
