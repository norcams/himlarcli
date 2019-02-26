#!/usr/bin/env python
import pprint
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
#from himlarcli.glance import Glance
from himlarcli import utils as himutils
from himlarcli.mail import Mail
#from himlarcli.state import State
from himlarcli.parser import Parser
from himlarcli.parser import Printer
import novaclient.exceptions as novaexc
import time
import sys

# OPS! It might need some updates. We use class Mail instead of Notify now.

himutils.is_virtual_env()

# Default value for date: today + 5 days at 14:00
today = datetime.today()
date = datetime(today.year, today.month, today.day, 15, 0) + timedelta(days=5)

# Load parser config from config/parser/*
parser = Parser()
parser.update_default('-m', date.strftime('%Y-%m-%d around %H:00'))
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=logger)
domain = 'Dataporten'
zone = '%s-default-1' % ksclient.region
msg_file = 'notify/notify_reboot.txt'

# aggregate in <loc>-legacy-1 AZ
legacy_aggregate = ['group1', 'group2', 'group3']

if 'host' in options and options.host:
    if '.' in options.host:
        host = options.host
    else:
        domain = ksclient.get_config('openstack', 'domain')
        host = options.host + '.' + domain
else:
    host = None

def action_show():
    aggregate = novaclient.get_aggregate(options.aggregate)
    print '\nMETADATA:'
    for key, value in aggregate.metadata.iteritems():
        print "%s = %s" % (key, value)
    print '\nHOSTS:'
    for h in aggregate.hosts:
        services = novaclient.get_service(h)
        print '%s (%s)' % (h, services[0].status)

def action_list():
    filters = dict()
    if options.az:
        filters['availability_zone'] = options.az
    aggregates = novaclient.get_filtered_aggregates(**filters)
    for aggregate in aggregates:
        header = '%s (%s)' % (aggregate.name, aggregate.availability_zone)
        enabled = 'active' if 'enabled' in aggregate.metadata else 'deactive'
        printer.output_dict({'header': header})
        if options.detailed:
            printer.output_dict(aggregate.to_dict())
        else:
            printer.output_dict({'name': aggregate.name, 'status': enabled})

def action_instances():
    instances = novaclient.get_instances(options.aggregate, host)
    pp = pprint.PrettyPrinter(indent=1)
    stats = dict()
    for i in instances:
        if i.status in stats:
            stats[i.status] += 1
        else:
            stats[i.status] = 1
        network = next(iter(i.addresses))
        print '%s %s (status=%s, network=%s)' % (i.id, unicode(i.name), i.status, network)
    print "\nSTATUS:"
    print "======="
    pp.pprint(stats)

def action_users():
    users = novaclient.get_users(options.aggregate, simple=True)
    for user in users:
        print user

def action_activate():
    aggregates = novaclient.get_aggregates()
    dry_run_txt = 'DRY-RUN: ' if options.dry_run else ''
    for aggregate in aggregates:
        # do not use on central1 or placeholder1
        if aggregate not in legacy_aggregate:
            continue
        print '=============== %s ================' % aggregate
        metadata = novaclient.get_aggregate(aggregate)
        # Enable this aggregate
        if aggregate == options.aggregate:
            for h in metadata.hosts:
                print '%sEnable %s' % (dry_run_txt, h)
                novaclient.enable_host(h)
            tags = {'enabled': datetime.today(), 'disabled': None, 'mail': None}
            if not options.dry_run:
                novaclient.update_aggregate(aggregate, tags)
        else: # Disable everything else
            for h in metadata.hosts:
                services = novaclient.get_service(h)
                if services[0].status == 'enabled':
                    print '%sDisable %s' % (dry_run_txt, h)
                    novaclient.disable_host(h)
            tags = {'disabled': datetime.today(), 'enabled': None}
            if not options.dry_run:
                novaclient.update_aggregate(aggregate, tags)

def action_migrate():
    # Find enabled aggregate
    aggregates = novaclient.get_aggregates()
    active_aggregate = 'unknown'
    for aggregate in aggregates:
        if aggregate not in legacy_aggregate:
            continue
        info = novaclient.get_aggregate(aggregate)
        if 'enabled' in info.metadata:
            active_aggregate = aggregate
            break
    q = 'Migrate all instances from %s to %s' % (options.aggregate, active_aggregate)
    if not himutils.confirm_action(q):
        return
    instances = novaclient.get_instances(options.aggregate, host)
    count = 0
    for instance in instances:
        count += 1
        if options.dry_run:
            logger.debug('=> DRY-RUN: migrate instance %s' % unicode(instance.name))
        else:
            logger.debug('=> migrate instance %s' % unicode(instance.name))
            try:
                instance.migrate()
                time.sleep(2)
                if count%options.limit == 0 and (options.hard_limit and count < options.limit):
                    logger.debug('=> sleep for %s seconds', options.sleep)
                    time.sleep(options.sleep)
            except novaexc.BadRequest as e:
                sys.stderr.write("%s\n" % e)
                sys.stderr.write("Error found. Cancel migration!\n")
                break
        if options.hard_limit and count >= options.limit:
            logger.debug('=> use of hard limit and exit after %s instances', options.limit)
            break

def action_notify():
    users = dict()
    instances = novaclient.get_instances(options.aggregate)
    # update metadata
    if not options.dry_run:
        metadata = {'mail': options.date}
        novaclient.update_aggregate(options.aggregate, metadata=metadata)
    # Generate instance list per user
    for i in instances:
        email = None
        user = ksclient.get_by_id('user', i.user_id)
        if not user:
            project = ksclient.get_by_id('project', i.tenant_id)
            if hasattr(project, 'admin'):
                email = project.admin
            else:
                continue
        if not email:
            if not user.name:
                continue
            if "@" not in user.name:
                continue
            email = user.name.lower()
        if email not in users:
            users[email] = dict()
        users[email][i.name] = {'status': i.status}
    if users:
        mapping = dict(region=ksclient.region.upper(),
                       date=options.date,
                       region_lower=ksclient.region.lower())
        body_content = himutils.load_template(inputfile=msg_file,
                                              mapping=mapping,
                                              log=ksclient.get_logger())
        if not body_content:
            print 'ERROR! Could not find and parse mail body in \
                  %s' % options.msg
            sys.exit(1)
        mail = Mail(options.config, debug=options.debug)
    # Email each users
    for user, instances in users.iteritems():
        user_instances = ""
        for server, info in instances.iteritems():
            user_instances += "%s (current status %s)\n" % (server, info['status'])
        msg = MIMEText(user_instances + body_content, 'plain', 'utf-8')
        msg['Subject'] = ('[UH-IaaS]: Your instances will be rebooted on %s (%s)'
                          % (options.date, ksclient.region))

        if not options.dry_run:
            mail.send_mail(user, msg)
            print "Sending email to user %s" % user
        else:
            print "Dry-run: Mail would be sendt to user %s" % user
    pp = pprint.PrettyPrinter(indent=1)
    print "\nComplete list of users and instances:"
    print "====================================="
    pp.pprint(users)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
