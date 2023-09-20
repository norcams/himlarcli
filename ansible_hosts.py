#!/usr/bin/env python
import configparser
import re
import utils
from himlarcli.foremanclient import ForemanClient
from himlarcli import utils as himutils

desc = 'Create an ansible inventory hostfile in ./hostfile.<loc>'
options = utils.get_options(desc, hosts=False)

foreman = ForemanClient(options.config, options.debug)
foreman.set_per_page(500)

hosts = foreman.get_hosts('*')
hostlist = dict()
for host in hosts['results']:
    var = None
    hostname = host['name'].split('.')[0]
    check = hostname.count('-')
    if check == 2:
        loc, role, num = hostname.split('-')
    #Example if test01-nat-linux-01
    if check == 3:
        loc, role, var, num = hostname.split('-')
    try:
        if not loc or not role:
            pass
    except:
        himutils.sys_error('Broken hostname %s! Please fix!' % hostname, 0)
        continue

    group = "%s-%s" % (loc, role)
    if not group in hostlist:
        hostlist[group] = []
    hostlist[group].append(hostname)

    # Add group for var
    if var:
        var_group = group = "%s-%s-%s" % (loc, role, var)
        if not var_group in hostlist:
            hostlist[var_group] = []
        hostlist[var_group].append(hostname)

children = "%s:children" % loc
filename = "hostfile.%s" % loc
nodes = "%s-nodes:children" % loc

exclude_nodes = {
    r'(bgo|osl)\-cephmon$',
    '.+storage',
    r'(bgo|osl|test01)\-object',
    '.+compute',
    '.+controller',
    '.+leaf',
    '.+torack',
    '.+spine',
    '.+login',
    r'(bgo|osl|test01)\-mgmt',
}
# creates something like "(.+spine)|(.+login)|(.+storage)|((bgo|osl)\-cephmon$)|...."
excludes_seperator = ")|("
combined_excludes = "(" + excludes_seperator.join(exclude_nodes) + ")"
pattern_excluded = re.compile(combined_excludes)

parser = configparser.ConfigParser(allow_no_value=True)
parser.add_section(children)
parser.add_section(nodes)

for section, hosts in sorted(hostlist.items()):
    parser.set(children, section)
    parser.add_section(section)
    if not pattern_excluded.match(section):
        parser.set(nodes, section)
    for host in hosts:
        parser.set(section, host)

with open(filename, 'w') as f:
    parser.write(f)
