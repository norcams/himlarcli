#!/usr/bin/env python

import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.ldapclient import LdapClient

options = utils.get_options('Print openstack user stats', hosts=False)
keystoneclient = Keystone(options.config, options.debug)
projects = keystoneclient.list_projects('dataporten')
logger = keystoneclient.get_logger()

conf = dict()
conf['uib'] = {
    'server': 'ldap.uib.no',
    'base_dn': 'dc=uib,dc=no',
    'type': 'employeeType',
    'org': 'ou'
}
conf['uio'] = {
    'server': 'ldap.uio.no',
    'base_dn': 'dc=uio,dc=no',
    'type': 'eduPersonPrimaryAffiliation:',
    'org': 'ou'
}

uib = LdapClient(options.config, conf['uib'], options.debug, logger)
uio = LdapClient(options.config, conf['uio'], options.debug, logger)

# Generate attr list for each location
for i in conf.keys():
    conf[i]['attr'] = [conf[i]['type'], conf[i]['org']]

for mail in projects:
    print "---------------- %s ------------------" % mail
    if 'uib' in mail:
        print uib.get_user(mail, attr=conf['uib']['attr'])
    elif 'uio' in mail:
        print uio.get_user(mail, attr=conf['uio']['attr'])
