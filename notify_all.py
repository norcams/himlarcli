#!/usr/bin/python
import sys
import utils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.notify import Notify
from email.mime.text import MIMEText

options = utils.get_options('Notify all users', dry_run=True, hosts=False)
keystone = Keystone(options.config, debug=options.debug)
notify = Notify(options.config, debug=options.debug)
region = keystone.region

# Edit this to send new email to all users
subject = 'UH-IaaS: Purge of all data (%s)' % region
body_file = 'misc/notify_reinstall.txt'

with open(body_file, 'r') as body_txt:
    body_content = body_txt.read()

projects = keystone.list_projects('Dataporten')
for project in projects:
    msg = MIMEText(body_content)
    msg['Subject'] = subject
    if not options.dry_run:
        notify.send_mail(project, msg)
    print '\nProject: %s' % project

notify.close()
