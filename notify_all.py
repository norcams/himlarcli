#!/usr/bin/python
import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.mail import Mail
from email.mime.text import MIMEText

# OPS! It might need some updates. We use class Mail instead of Notify now.

options = utils.get_options('Notify all users', dry_run=True, hosts=False)
keystone = Keystone(options.config, debug=options.debug)
mail = Mail(options.config, debug=options.debug)
region = keystone.region

print "Remove these lines if you want to run this and send mail to all!"
sys.exit(0)

# Edit this to send new email to all users
subject = 'UH-IaaS: Purge of all data (%s)' % region
body_file = 'notify/notify_reinstall.txt'

with open(body_file, 'r') as body_txt:
    body_content = body_txt.read()

projects = keystone.list_projects('Dataporten')
for project in projects:
    msg = MIMEText(body_content)
    msg['Subject'] = subject
    if not options.dry_run:
        mail.send_mail(project, msg)
    print '\nProject: %s' % project

mail.close()
