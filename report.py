#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
from prettytable import PrettyTable
import re
import sys

utils.is_virtual_env()

parser = Parser()
parser.set_autocomplete(True)
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
ksclient.set_domain(options.domain)
logger = ksclient.get_logger()

if hasattr(options, 'region'):
    regions = ksclient.find_regions(region_name=options.region)
else:
    regions = ksclient.find_regions()

if not regions:
    utils.sys_error('no regions found with this name!')

#---------------------------------------------------------------------
# Main functions
#---------------------------------------------------------------------
def action_show():
    project = ksclient.get_project_by_name(project_name=options.project)
    if not project:
        utils.sys_error('No project found with name %s' % options.project)
    Printer.prettyprint_project_metadata(project, options, logger, regions)
    if options.detail:
        Printer.prettyprint_project_zones(project, options, logger)
        Printer.prettyprint_project_volumes(project, options, logger, regions)
        Printer.prettyprint_project_images(project, options, logger, regions)
        Printer.prettyprint_project_instances(project, options, logger, regions)

def action_list():
    search_filter = dict()
    if options.filter and options.filter != 'all':
        search_filter['type'] = options.filter
    projects = ksclient.get_projects(**search_filter)

    # Project counter
    count = 0

    # Loop through projects
    for project in projects:
        Printer.prettyprint_project_metadata(project, options, logger, regions)
        if options.detail:
            Printer.prettyprint_project_zones(project, options, logger)
            Printer.prettyprint_project_volumes(project, options, logger, regions)
            Printer.prettyprint_project_images(project, options, logger, regions)
            Printer.prettyprint_project_instances(project, options, logger, regions)

        # Print some vertical space and increase project counter
        print "\n\n"
        count += 1

    # Finally print out number of projects
    printer.output_dict({'header': 'Project list count', 'count': count})

def action_user():
    if not ksclient.is_valid_user(email=options.user, domain=options.domain):
        print "%s is not a valid user. Please check your spelling or case." % options.user
        sys.exit(1)
    user = ksclient.get_user_objects(email=options.user, domain=options.domain)

    # Project counter
    count = 0

    for project in user['projects']:
        if options.admin and project.admin != options.user:
            continue
        Printer.prettyprint_project_metadata(project, options, logger, regions)
        if options.detail:
            Printer.prettyprint_project_zones(project, options, logger)
            Printer.prettyprint_project_volumes(project, options, logger, regions)
            Printer.prettyprint_project_images(project, options, logger, regions)
            Printer.prettyprint_project_instances(project, options, logger, regions)

        # Print some vertical space and increase project counter
        print "\n\n"
        count += 1

    # Finally print out number of projects
    printer.output_dict({'header': 'Project list count', 'count': count})

#---------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------


#=====================================================================
# Main program
#=====================================================================
# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
