#!/usr/bin/env python

import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.ldapclient import LdapClient

options = utils.get_options('Print openstack user stats', hosts=False)
keystoneclient = Keystone(options.config, debug=options.debug)
projects = keystoneclient.list_projects('dataporten')
logger = keystoneclient.get_logger()

count = dict()
count['type'] = { 'staff': 0, 'student': 0, 'faculty': 0 }

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
    'type': 'eduPersonPrimaryAffiliation',
    'org': 'eduPersonPrimaryOrgUnitDN'
}

uib = LdapClient(options.config, conf['uib'], options.debug, logger)
uio = LdapClient(options.config, conf['uio'], options.debug, logger)

# Generate attr list for each location
for i in conf.keys():
    conf[i]['attr'] = [conf[i]['type'], conf[i]['org']]

for mail in projects:
    logger.debug("=> ----- %s -----" % mail)
    if 'uib' in mail:
        # student
        if 'student' in mail:
            count['type']['student'] += 1
            logger.debug("=> count:type:student: +1")
        else:
            search = uib.get_user(mail, attr=conf['uib']['attr'])
            if len(search) > 0:
                user = search[0]
                if 'IT-avdelingen' in user[1][conf['uib']['org']]:
                    count['type']['staff'] += 1
                    logger.debug("=> count:type:staff: +1 (IT-avdelingen)")
                elif 'Kommunikasjonsavdelingen' in user[1][conf['uib']['org']]:
                    count['type']['staff'] += 1
                    logger.debug("=> count:type:staff: +1 Kommunikasjonsavdelingen")
                else:
                    count['type']['faculty'] += 1
                    logger.debug("=> count:type:faculty: +1 %s" % user[1][conf['uib']['org']])
            else:
                print 'Unknown user %s' % mail
    elif 'uio' in mail:
        search = uio.get_user(mail, attr=conf['uio']['attr'])
        if len(search) > 0:
            user = search[0]
            if user[1][conf['uio']['type']][0]:
                count['type'][user[1][conf['uio']['type']][0]] += 1
                logger.debug("=> count:type:%s: +1" % user[1][conf['uio']['type']][0])
                logger.debug('=> org: %s' % user[1][conf['uio']['org']][0])
            else:
                print user
        else:
            print 'Unknown user %s' % mail


print count
