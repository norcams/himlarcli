#!/usr/bin/env python
import sys
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
logger = ksclient.get_logger()
printer = Printer(options.format)

project_types = himutils.load_config('config/type.yaml', log=logger)
if options.type and options.type not in project_types['types']:
    sys.stderr.write("Project type %s not valid. See config/type.yaml\n"
                     % options.type)
    sys.exit(1)

def action_list():
    search_filter = dict()
    if options.type:
        search_filter['type'] = options.type
    projects = ksclient.get_projects(domain=options.domain, **search_filter)
    regions = ksclient.get_regions()
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region.id)
        for project in projects:
            if not options.filter or options.filter in project.name:
                #print "found %s" % project.name
                #printer.output_dict(project.to_dict())
                instances = novaclient.get_project_instances(project.id)
                for i in instances:
                    print '%s %s %s (%s)' % (i.id, i.status, unicode(i.name), project.name)


# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
