#!/usr/bin/env python
import time
from himlarcli.mail import Mail

sendmail = 'notify/user_emails.txt'

file = open(sendmail, "r")
print(file.read()) #test
users = file.read()
msg = "dett er en test"
print(mail.send_mail(emails, msg, fromaddr='no-reply@uh-iaas.no')

  for user in file:
    #mapping = dict(project_name=options.project, admin=project.admin)
    #body_content = himutils.load_template(inputfile=access_user_msg_file,
    #                                      mapping=mapping)
    msg = MIMEText(body_content, 'plain')
    msg['subject'] = 'UH-IaaS: You have been given access to project %s' % options.project

    mail.send_mail(user, msg, fromaddr='no-reply@uh-iaas.no')
