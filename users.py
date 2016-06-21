#!/usr/bin/env python

import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.ldapclient import LdapClient

options = utils.get_options('Print openstack user stats', hosts=False)
keystoneclient = Keystone(options.config, options.debug)
projects = keystoneclient.list_projects('dataporten')
logger = keystoneclient.get_logger()
ldapclient = LdapClient(options.config, options.debug, logger)

for mail in projects:
    print "---------------- %s ------------------" % mail
    print ldapclient.get_user(mail)
