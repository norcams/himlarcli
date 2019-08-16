#!/usr/bin/env python
import sys
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_domain('Dataporten')
logger = ksclient.get_logger()
printer = Printer(options.format)

# Regions
regions = himutils.load_region_config('config/stats',
                                      region=ksclient.region,
                                      log=logger)
""" ACTIONS """

def project():
    stats = {'demo': 0,
             'personal': 0,
             'research': 0,
             'education': 0,
             'admin': 0,
             'test': 0,
             'total': 0}
    for name in sorted(regions['regions'].iterkeys()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()
        stats['total'] += len(instances)
        for i in instances:
            project = ksclient.get_by_id('project', i.tenant_id)
            if not project:
                sys.stderr.write("MISSING PROJECT! id=%s for instance %s\n" % (i.tenant_id, i.name))
                continue
            if hasattr(project, 'course'):
                stats['education'] += 1
            elif '@' in project.name:
                stats['personal'] += 1
            else:
                if hasattr(project, 'type'):
                    if project.type not in stats:
                        print "unknown project type %s for %s" % (project.type, project.name)
                    else:
                        stats[project.type] += 1
                else:
                    stats['admin'] += 1
    if options.output == 'count':
        stats['header'] = 'Number of instances grouped by instance type:'
        printer.output_dict(stats)
    else:
        percent = dict()
        if stats['total'] > 0:
            for s in sorted(stats):
                percent[s] = (float(stats[s])/float(stats['total']))*100
        percent['header'] = 'Percent of instances grouped by instance type:'
        printer.output_dict(percent)

def users():
    stats = dict()
    stats['total'] = 0
    for name in sorted(regions['regions'].iterkeys()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()
        stats['total'] += len(instances)
        for i in instances:
            user = ksclient.get_by_id('user', i.user_id)
            if not user:
                org = 'unknown'
                logger.debug('=> unknown user for %s (id=%s)' % (i.name, i.id))
            elif '@' not in user.name:
                org = 'sysuser'
            else:
                org = user.name.split("@")[1]
            if org in stats:
                stats[org] += 1
            else:
                stats[org] = 1
    if options.output == 'count':
        stats['header'] = 'Usage grouped by user email domain:'
        printer.output_dict(stats)
    else:
        percent = dict()
        if stats['total'] > 0:
            for s in sorted(stats):
                percent[s] = (float(stats[s])/float(stats['total']))*100
        percent['header'] = 'Percentage of instances grouped by users email domain:'
        printer.output_dict(percent)

def org():
    stats = dict()
    stats['total'] = 0
    for name in sorted(regions['regions'].iterkeys()):
        logger.debug('=> count region %s' % name)
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
        instances = novaclient.get_instances()
        stats['total'] += len(instances)
        for i in instances:
            user = ksclient.get_by_id('user', i.user_id)
            if not user:
                org = 'unknown'
                logger.debug('=> unknown user for %s (id=%s)' % (i.name, i.id))
            elif '@' not in user.name:
                org = 'sysuser'
            else:
                domain = user.name.split("@")[1]
                if len(domain.split(".")) > 1:
                    org = domain.split(".")[-2]
                else:
                    org = 'unknown'
            if org in stats:
                stats[org] += 1
            else:
                stats[org] = 1
    if options.output == 'count':
        stats['header'] = 'Usage grouped by user organization:'
        printer.output_dict(stats)
    else:
        percent = dict()
        if stats['total'] > 0:
            for s in sorted(stats):
                percent[s] = (float(stats[s])/float(stats['total']))*100
        percent['header'] = 'Percentage of instances grouped by users organization:'
        printer.output_dict(percent)

def user():
    if not ksclient.is_valid_user(email=options.email):
        print "%s is not a valid user. Please check your spelling or case." % options.email
        sys.exit(1)
    obj = ksclient.get_user_objects(email=options.email, domain='Dataporten')
    projects = obj['projects']
    total = 0
    for project in projects:
        project_type = project.type if hasattr(project, 'type') else 'unknown'
        print "\n%s (type=%s):" % (project.name, project_type)
        for name in sorted(regions['regions'].iterkeys()):
            logger.debug('=> count region %s' % name)
            novaclient = Nova(options.config, debug=options.debug, log=logger, region=name)
            instances = novaclient.get_project_instances(project.id)
            total += len(instances)
            for i in instances:
                print "* %s" % i.name
    print "\nTotal number of instances for %s: %s" % (options.email, total)

def rename():
    if hasattr(options, 'region'):
        regions = ksclient.find_regions(region_name=options.region)
    else:
        regions = ksclient.find_regions()
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        instance = nc.get_instance(options.serverid)
        if not instance:
            himutils.sys_error('No project found with name %s' % options.serverid)
        instance.update(name=options.name, description=options.desc)


# Run local function with the same name as the action
action = locals().get(options.action)
if not action:
    logger.error("Action %s not implemented" % options.action)
    sys.exit(1)
action()
