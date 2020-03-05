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
    if not utils.confirm_action('Rename UiO users and send mail?'):
        return
    mail = Mail(options.config, debug=options.debug)
    mail.set_dry_run(options.dry_run)
    fromaddr = "support@uh-iaas.no"
    template_file = 'notify/mail_uio_feide2.txt'
    logfile = 'logs/uio_mail_sent2.log'
    subject = '[NREC] Your username and project name has been changed'
    users = kc.get_users(domain=options.domain)
    if not users:
        utils.sys_error('users mapping file empty!')
    mapping = load_uio_users(options.inputfile)
    for u in users:
        if not re.search(r"^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uio\.no$", u.name):
            continue
        if u.name not in mapping:
            utils.sys_error('could not find mapping for %s' % u.name, 0)
            continue
        print 'rename %s' % u.name
        changes = kc.rename_user(mapping[u.name], u.name)
        changes_txt = "\nThe following change has been made to your username:\n"
        changes_txt += "%s => %s\n" % (u.name, mapping[u.name])
        changes_txt += "\nThe following change has been made to your project name:\n"
        for old_p, new_p in changes['projects'].iteritems():
            changes_txt += "%s => %s\n" % (old_p, new_p)
        body_content = utils.load_template(inputfile=template_file,
                                           mapping={'changes': changes_txt},
                                           log=logger)
        msg = mail.get_mime_text(subject, body_content, fromaddr)
        mail.send_mail(u.name, msg, fromaddr)
        if not options.dry_run:
            utils.append_to_file(logfile, u.name)
        print 'mail sent to %s' % u.name
    mail.close()

def action_check():
    users = kc.get_users(domain=options.domain)
    if not users:
        utils.sys_error('users mapping file empty!')
    mapping = load_uio_users(options.inputfile)
    printer.output_dict({'header': 'Users not found in mapping csv:'})
    output = dict({'unknown': []})
    found = dict()
    count = 0
    for u in users:
        if not re.search(r"^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uio\.no$", u.name):
            continue
        if u.name not in mapping:
            output['unknown'].append(u.name)
            count += 1
        else:
            if mapping[u.name] in found:
                utils.sys_error('multiple mapping to %s' % mapping[u.name], 0)
                utils.sys_error('both %s and %s map to %s' % (u.name, found[mapping[u.name]], mapping[u.name]), 0)
            else:
                found[mapping[u.name]] = u.name
    printer.output_dict(output)
    printer.output_dict({'header': 'Count', 'users': count})


def action_notify():
    if not utils.confirm_action('Send mail to all UiO users?'):
        return
    mail = utils.get_client(Mail, options, logger, None)
    fromaddr = mail.get_config('mail', 'from_addr')
    logfile = 'logs/uio_mail_sent.log'
    subject = '[NREC] Changes to username and project name for UiO users'

    users = kc.get_users(domain=options.domain)
    for u in users:
        if not re.search(r"^[a-z0-9]+[\.'\-a-z0-9_]*[a-z0-9]+@[\.'\-a-z0-9_]*uio\.no$", u.name):
            if 'uio' in u.name:
                print "User %s not matched as uio-user. Please check" % u.name
            continue
        body_content = utils.load_template(inputfile=options.template,
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
