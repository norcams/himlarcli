#!/usr/bin/env python
import pprint
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.glance import Glance
from himlarcli import utils as himutils
from himlarcli.notify import Notify
from himlarcli.state import State

import sys
import utils

himutils.is_virtual_env()

desc = 'Mange host aggregate groups of compute nodes. \
        Note that notify sends email to users!'
actions = ['hosts', 'instances', 'users', 'notify', 'migrate', 'activate']
# Default date for notify are today at 14:00 + 5 days
d = datetime.today()
date = datetime(d.year, d.month, d.day, 14, 0) + timedelta(days=5)
date = date.strftime('%Y-%m-%d around %H:00')
opt_args = {
    '-n': {
        'dest': 'aggregate',
        'help': 'aggregate name',
        'required': True,
        'metavar': 'name'},
    '-m': {
        'dest': 'date',
        'help': 'date message',
        'default': date,
        'metavar': 'date'},
    '--save': {
        'dest': 'save',
        'help': 'save instance states',
        'action': 'store_const',
        'const': True},
    '--stage': {
        'dest': 'stage',
        'help': 'migration stage',
        'default': 'reactivate'}}

options = utils.get_action_options(desc, actions,
                                   opt_args=opt_args, dry_run=True)
ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
novaclient = Nova(options.config, debug=options.debug, log=logger)
domain = 'Dataporten'
zone = '%s-default-1' % ksclient.region
msg_file = 'misc/notify_reboot.txt'

""" ACTIONS """


def hosts():
    aggregate = novaclient.get_aggregate(options.aggregate)
    for host in aggregate.hosts:
        services = novaclient.get_service(host)
        print '%s (%s)' % (host, services[0].status)

def instances():
    instances = novaclient.get_instances(options.aggregate)
    pp = pprint.PrettyPrinter(indent=1)
    stats = dict()
    for i in instances:
        if i.status in stats:
            stats[i.status] += 1
        else:
            stats[i.status] = 1
        print '%s (status=%s)' % (i.name, i.status)
    print "\nSTATUS:"
    print "======="
    pp.pprint(stats)

def users():
    users = novaclient.get_users(options.aggregate, simple=True)
    for user in users:
        print user

def activate():
    aggregates = novaclient.get_aggregates()
    for aggregate in aggregates:
        print '=============== %s ================' % aggregate
        metadata = novaclient.get_aggregate(aggregate)
        # Enable this aggregate
        if aggregate == options.aggregate:
            for host in metadata.hosts:
                print 'Enable %s' % host
                novaclient.enable_host(host)
            tags = {'enabled': datetime.today()}
            novaclient.update_aggregate(aggregate, tags)
        else: # Disable everything else
            for host in metadata.hosts:
                services = novaclient.get_service(host)
                if services[0].status == 'enabled':
                    print 'Disable %s' % host
                    novaclient.disable_host(host)
            tags = {'disabled': datetime.today()}
            novaclient.update_aggregate(aggregate, tags)

def migrate():
    state = State(options.config, debug=options.debug, log=logger)
    glclient = Glance(options.config, debug=options.debug, log=logger)
    print 'STAGE=%s' % options.stage

    # stage: purge state
    if options.stage == 'purge':
        state.purge(state.IMAGE_TABLE)
    # stage: reactivate images
    if options.stage == 'reactivate':
        filters = {'status': 'deactivated'}
        images = glclient.get_images(filters=filters)
        for image in images:
            # Save image status
            state.insert(state.IMAGE_TABLE, id=image.id, region=ksclient.region,
                         status=image.status, name=image.name)
            # Reactivate image
            glclient.reactivate(image.id)
    # stage: deactivate images
    if options.stage == 'deactivate':
        images = state.fetch(state.IMAGE_TABLE, columns='id, status', status='deactivated')
        for image in images:
            glclient.deactivate(image_id=image[0])


def notify():
    users = dict()
    instances = novaclient.get_instances(options.aggregate)
    # update metadata
    if not options.dry_run:
        metadata = {'notify': options.date}
        novaclient.update_aggregate(options.aggregate, metadata=metadata)
    # Generate instance list per user
    for i in instances:
        user = ksclient.get_user_by_id(i.user_id)
        if not hasattr(user, 'name'):
            continue
        if "@" not in user.name:
            continue
        email = user.name.lower()
        if email not in users:
            users[email] = dict()
        users[email][i.name] = {'status': i.status}
    if users:
        mapping = dict(region=ksclient.region.upper(), date=options.date)
        body_content = himutils.load_template(inputfile=msg_file,
                                              mapping=mapping,
                                              log=ksclient.get_logger())
        if not body_content:
            print 'ERROR! Could not find and parse mail body in \
                  %s' % options.msg
            sys.exit(1)
        notify = Notify(options.config, debug=options.debug)
    # Email each users
    for user, instances in users.iteritems():
        # FIXME unicode server
        user_instances = ""
        for server, info in instances.iteritems():
            user_instances += "%s (current status %s)\n" % (server, info['status'])
        msg = MIMEText(user_instances + body_content)
        msg['Subject'] = 'UH-IaaS: Rebooting instance (%s)' % ksclient.region
        if not options.dry_run:
            notify.send_mail(user, msg)
            print "Sending email to user %s" % user
        else:
            print "Dry-run: Mail would be sendt to user %s" % user
    pp = pprint.PrettyPrinter(indent=1)
    print "\nComplete list of users and instances:"
    print "====================================="
    pp.pprint(users)

# Run local function with the same name as the action
action = locals().get(options.action[0])
if not action:
    logger.error("Action %s not implemented" % options.action[0])
    sys.exit(1)
action()
