#!/usr/bin/env python
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.glance import Glance
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

himutils.is_virtual_env()

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

ksclient = Keystone(options.config, debug=options.debug)
ksclient.set_dry_run(options.dry_run)
logger = ksclient.get_logger()

regions = ksclient.find_regions()

def action_disabled():
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        printer.output_dict({'header': '%s: Instances in disabled project (host, name, project)'
                                       % region})
        groups = {'group1': 0, 'group2': 0, 'group3': 0}
        count = 0
        for i in instances:
            project = ksclient.get_by_id('project', i.tenant_id)
            if project.enabled:
                continue
            host = getattr(i, 'OS-EXT-SRV-ATTR:host').split('.')[0]
            output = {'name': i.name, 'project': project.name, 'status': host}
            printer.output_dict(output, sort=True, one_line=True)
            if '01' in host or '04' in host:
                groups['group1'] += 1
            elif '02' in host or '05' in host:
                groups['group2'] += 1
            elif '03' in host or '06' in host:
                groups['group3'] += 1
            count += 1
        output = {'header': 'Instance count', 'total': count}
        output.update(groups)
        printer.output_dict(output)

def action_nodiscard():
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        glclient = Glance(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        printer.output_dict({'header': '%s: Instances without discard (image, name, visibility)'
                                       % region})
        count = 0
        for i in instances:
            image = glclient.get_image_by_id(i.image['id'])
            # Asume that hw_disk_bus == discard
            if 'hw_disk_bus' in image:
                continue
            output = {'name': i.name, 'image': image['name'], 'status': image['visibility']}
            printer.output_dict(output, sort=True, one_line=True)
            count += 1
        printer.output_dict({'header': 'Instance count', 'count': count})


# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
