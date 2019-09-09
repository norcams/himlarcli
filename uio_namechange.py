#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.mail import Mail
from himlarcli import utils #as himutils
import re
import os
import csv

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

def action_rename():
    # mail = Mail(options.config, debug=options.debug)
    # mail.set_dry_run(options.dry_run)
    # fromaddr = mail.get_config('mail', 'from_addr')
    # template_file = 'notify/mail_uio_feide.txt'
    # logfile = 'logs/uio_mail_sent.log'
    # subject = '[UH-IaaS] Changes to username and project name for UiO users'
    # users = kc.get_users(domain=options.domain)
    # if not users:
    #     utils.sys_error('users mapping empty!')
    # mapping = load_uio_users('mail_changes.csv')
    # for u in users:
    #     if not re.search("^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uib\.no$", u.name):
    #         continue
    #     print mapping[u.name]
    pass

def action_check():
    users = kc.get_users(domain=options.domain)
    if not users:
        utils.sys_error('users mapping file empty!')
    mapping = load_uio_users(options.inputfile)
    printer.output_dict({'header': 'Users not found in mapping csv:'})
    output = dict({'unknown': []})
    for u in users:
        if not re.search(r"^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uio\.no$", u.name):
            continue
        if u.name not in mapping:
            output['unknown'].append(u.name)
    printer.output_dict(output)

def action_notify():
    if not utils.confirm_action('Send mail to all UiO users?'):
        return
    mail = utils.get_client(Mail, options, logger, None)
    fromaddr = mail.get_config('mail', 'from_addr')
    template_file = 'notify/mail_uio_feide.txt'
    logfile = 'logs/uio_mail_sent.log'
    subject = '[UH-IaaS] Changes to username and project name for UiO users'

    users = kc.get_users(domain=options.domain)
    for u in users:
        if not re.search(r"^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uio\.no$", u.name):
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

def load_uio_users(inputfile):
    inputfile = utils.get_abs_path(inputfile)
    if not os.path.isfile(inputfile):
        utils.sys_error('file not found: %s' % inputfile)
        return None
    users = dict()
    with open(inputfile, mode='r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=':')
        header = True
        for row in csv_reader:
            # drop header row
            if header:
                header = False
                continue
            users[row[0]] = row[1]
    return users


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
