#!/usr/bin/env python
import sys
from email.mime.text import MIMEText
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.notify import Notify

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
printer = Printer(options.format)
msg_file = 'misc/notify_cleanup.txt'

# Project type
project_types = himutils.load_config('config/type.yaml', log=logger)
if options.type and options.type not in project_types['types']:
    sys.stderr.write("Project type %s not valid. See config/type.yaml\n"
                     % options.type)
    sys.exit(1)

# Region
regions = list()
if options.region:
    regions = regions.append(options.region)
else:
    for region in  ksclient.get_regions():
        regions.append(region.id)
logger.debug('=> active regions: %s' % regions)

def action_list():
    search_filter = dict()
    if options.type:
        search_filter['type'] = options.type
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    #regions = ksclient.get_regions()
    count = 0
    for region in regions:
        #print "==============\n REGION=%s\n==============" % region
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        for project in projects:
            if not options.filter or options.filter in project.name:
                #print "found %s" % project.name
                #printer.output_dict(project.to_dict())
                instances = novaclient.get_project_instances(project.id)
                for i in instances:
                    count += 1
                    output = dict()
                    output['_region'] = region
                    output['id'] = i.id
                    output['status'] = i.status
                    output['name'] = unicode(i.name)
                    output['project'] = project.name
                    printer.output_dict(objects=output, one_line=True)
                    #print '%s %s %s (%s)' % (i.id, i.status, unicode(i.name), project.name)
    print "\nTotal number of instances for cleanup: %s" % count

def action_notify():
    search_filter = dict()
    if options.type:
        search_filter['type'] = options.type
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    for region in regions:
        users = dict()
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        for project in projects:
            if not options.filter or options.filter in project.name:
                instances = novaclient.get_project_instances(project.id)
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
            mapping = dict(region=region)
            body_content = himutils.load_template(inputfile=msg_file,
                                                  mapping=mapping,
                                                  log=logger)
            if not body_content:
                print 'ERROR! Could not find and parse mail body in \
                      %s' % options.msg
                sys.exit(1)
            notify = Notify(options.config, debug=options.debug)
        # Email each users
        for user, instances in users.iteritems():
            user_instances = ""
            for server, info in instances.iteritems():
                user_instances += "%s (current status %s)\n" % (server, info['status'])
            msg = MIMEText(user_instances + body_content, 'plain', 'utf-8')
            msg['Subject'] = ('UH-IaaS: Your instances will be terminated (%s)' % (region))

            if not options.dry_run:
                notify.send_mail(user, msg)
                print "Sending email to user %s" % user
            else:
                print "Dry-run: Mail would be sendt to user %s" % user
        print "\nComplete list of users and instances:"
        print "====================================="
        printer.output_dict(users)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
