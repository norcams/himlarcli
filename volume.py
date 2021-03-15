#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.cinder import Cinder
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Check if region options is used and if it is a valid region
if options.region and options.region in kc.find_regions(options.region):
    region = options.region
else:
    region = kc.get_region() # use default from config

def action_list():
    search_opts = {}
    if options.project:
        project = kc.get_project_by_name(project_name=options.project)
        if not project:
            utils.sys_error('Project {} not found'.format(options.project))
        search_opts['project_id'] = project.id
    else:
        project_id = None
    cc = Cinder(options.config, debug=options.debug, log=logger, region=region)
    volumes = cc.get_volumes(detailed=True, search_opts=search_opts)
    printer.output_dict({'header': 'Volumes (id, name, type)'})
    count = {'count': 0, 'size': 0}
    for volume in volumes:
        if options.type and options.type != volume.volume_type:
            continue
        count = print_and_count(volume, count)
    printer.output_dict({
        'header': 'Count',
        'volumes': count['count'],
        'size': count['size']})

def action_orphan():
    question = "This will also purge all orphan volumes. Are you sure?"
    if options.purge and not utils.confirm_action(question):
        return
    cc = utils.get_client(Cinder, options, logger, region)
    volumes = cc.get_volumes(detailed=True)
    printer.output_dict({'header': 'Volumes (id, name, type)'})
    count = {'count': 0, 'size': 0}
    for volume in volumes:
        project = kc.get_by_id('project', getattr(volume, 'os-vol-tenant-attr:tenant_id'))
        if project: # not orphan volume
            continue
        count = print_and_count(volume, count)
        if options.purge:
            cc.delete_volume(volume.id, True)
    printer.output_dict({
        'header': 'Count',
        'volumes': count['count'],
        'size': count['size']})

def print_and_count(volume, count):
    output = {
        '0': volume.id,
        '5': volume.name,
        '3': volume.volume_type,
        '1': volume.size
    }
    count['count'] += 1
    count['size'] += volume.size
    printer.output_dict(output, one_line=True)
    return count

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
