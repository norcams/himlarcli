#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
#from himlarcli.cinder import Cinder
from himlarcli.gnocchi import Gnocchi
from himlarcli.cinder import Cinder
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from datetime import date, timedelta
from collections import OrderedDict

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc= Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Billing will always use all regions
regions = kc.find_regions()

def action_whales():
    start = himutils.get_date(options.start, date.today() - timedelta(days=1))
    stop = himutils.get_date(options.end, date.today() + timedelta(days=1))
    if start > stop:
        himutils.sys_error('start %s must be fore stop %s' % (start, stop))
    logger.debug('=> start date = %s', start)
    logger.debug('=> stop date = %s', stop)

    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        cc = Cinder(options.config, debug=options.debug, log=logger, region=region)
        project_usage = nc.get_usage(start=start, end=stop)
        logger.debug('=> threshold for whales filter %s', options.threshold)
        print_header = True
        for usage in project_usage:
            project = kc.get_by_id(obj_type='project', obj_id=usage.tenant_id)
            if not project:
                logger.debug('=> project with id %s not found',usage.tenant_id)
                continue
            if len(usage.server_usages) < options.threshold:
                continue
            cinderusage = cc.get_usage(usage.tenant_id)
            admin = project.admin if hasattr(project, 'admin') else 'unknown!'
            output = OrderedDict()
            output['instances'] = len(usage.server_usages)
            output['volume_gb'] =  cinderusage.gigabytes['in_use']
            output['name'] = project.name
            output['admin'] = admin
            if print_header:
                output['header'] = 'project usage %s (instances, volume (GB), name, id)' % region
                print_header = False
            printer.output_dict(objects=output, sort=False, one_line=True)

def action_flavors():
    project = kc.get_project_by_name(options.project)
    start = himutils.get_date(options.start, date.today() - timedelta(days=1))
    stop = himutils.get_date(options.end, date.today() + timedelta(days=1))
    if start > stop:
        himutils.sys_error('start %s must be fore stop %s' % (start, stop))
    logger.debug('=> start date = %s', start)
    logger.debug('=> stop date = %s', stop)

    flavors = dict()
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        usage = nc.get_usage(project_id=project.id, start=start, end=stop)
        for server in usage.server_usages:
            flavors[server['flavor']] = flavors.get(server['flavor'], 0) + 1
    printer.output_dict({'header': 'flavor usage for %s in all regions' % project.name})
    printer.output_dict(flavors)

def action_resources():
    project = kc.get_project_by_name(options.project)
    start = himutils.get_date(options.start, date.today() - timedelta(days=1))
    stop = himutils.get_date(options.end, date.today() + timedelta(days=1))
    logger.debug('=> start date = %s', start)
    logger.debug('=> stop date = %s', stop)
    output = dict({'vcpu': 0, 'ram':0})
    for region in regions:
        # instances
        nc = Nova(options.config, debug=options.debug, log=logger)
        gc = Gnocchi(options.config, debug=options.debug, log=logger)
        deleted = nc.get_project_instances(project_id=project.id, deleted=True)
        running = nc.get_project_instances(project_id=project.id)
        for i in deleted + running:
            metrics = dict()
            metrics['vcpu'] = gc.get_client().metric.get('vcpus', i.id)
            metrics['ram'] = gc.get_client().metric.get('memory', i.id)
            for key, value in metrics.iteritems():
                measurement = gc.get_client().metric.get_measures(metric=value['id'],
                                                                  aggregation='max',
                                                                  start=start,
                                                                  stop=stop)
                if measurement:
                    output[key] += measurement[0][2]
    printer.output_dict({'header': 'resources used by %s in all regions' % project.name})
    printer.output_dict(output)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
