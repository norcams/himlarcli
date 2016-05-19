#!/usr/bin/python
import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.notify import Notify
from email.mime.text import MIMEText

options = utils.get_host_options('Notify users of rebuild host', hosts=1)

# Find region
keystoneclient = Keystone(options.config)
region = keystoneclient.get_region()

# Find users
novaclient = Nova(options.config, options.host[0])
if not novaclient.valid_host():
    print "ERROR: could not find host %s" % options.host[0]
    sys.exit(1)
toaddr = novaclient.list_users()

# Optional from file
#fp = open('users.txt', 'rb')
#toaddr = list()
#for line in fp:
#    if line != '\n':
#        toaddr.append(line)

with open('misc/notify_email.txt', 'r') as body_txt:
    body = body_txt.read()

msg = MIMEText(body)
msg['Subject'] = 'UH-IaaS: Terminating instance (%s)' % region

notify = Notify(options.config)
notify.send_mail(toaddr, msg, debug=0)

print '\nTo:' + ', '.join(toaddr)
print 'Subject: %s' % msg['Subject']
print "\n" + body + "\n"
