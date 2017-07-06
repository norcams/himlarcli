#!/usr/bin/env python
import sys
import time
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

def action_delete():
    q = "Delete these instances? (yes|no) "
    answer = raw_input(q)
    if answer.lower() != 'yes':
        print "Abort delete!"
        return
    search_filter = dict()
    if options.type:
        search_filter['type'] = options.type
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
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
                    logger.debug('=> DELETE %s (%s)' % (i.name, project.name))
                    if not options.dry_run:
                        i.delete()
                        count += 1
                        time.sleep(5)
    print "\nTotal number of instances deleted: %s" % count

def action_notify():
    q = "Send mail to all users of these instances about termination? (yes|no) "
    answer = raw_input(q)
    if answer.lower() != 'yes':
        print "Abort sending mail!"
        return

    search_filter = dict()
    if options.type:
        search_filter['type'] = options.type
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        for project in projects:
            if not options.filter or options.filter in project.name:
                instances = novaclient.get_project_instances(project.id)
                mapping = dict(region=region.upper(), project=project.name)
                body_content = himutils.load_template(inputfile=options.template,
                                                      mapping=mapping,
                                                      log=logger)
                subject = ('UH-IaaS: Your instances will be terminated (%s)' % (region))

                notify = Notify(options.config, debug=False, log=logger)
                notify.set_keystone_client(ksclient)
                notify.set_dry_run(options.dry_run)
                users = notify.mail_instance_owner(instances, body_content, subject)
                notify.close()
                print users

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
