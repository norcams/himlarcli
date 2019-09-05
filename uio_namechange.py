#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli import utils #as himutils
import re

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

def action_notify():
    mail = Mail(options.config, debug=options.debug)
    mail.set_dry_run(options.dry_run)
    fromaddr = mail.get_config('mail', 'from_addr')
    template_file = 'notify/mail_uio_feide.txt'
    logfile = 'logs/uio_mail_sent.log'
    subject = '[UH-IaaS] Changes to user and project name for UiO users'

    users = kc.get_users(domain=options.domain)
    for u in users:
        if not re.search("^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uio\.no$", u.name):
            if 'uio' in u.name:
                print "User %s not matched as uio-user. Please check" % u.name
            continue
        body_content = utils.load_template(inputfile=template_file,
                                           mapping={},
                                           log=logger)
        msg = mail.get_mime_text(subject, body_content, fromaddr)
        mail.send_mail(u.name, msg, fromaddr)
        if not options.dry_run:
            utils.append_to_file(logfile, u.name)
        print 'mail sent to %s' % u.name
    mail.close()

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
