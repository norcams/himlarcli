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
        printer.output_dict({'header': 'Instances in disabled project (name, project, state)'})
        count = 0
        for i in instances:
            project = ksclient.get_by_id('project', i.tenant_id)
            if project.enabled:
                continue
            output = {'name': i.name, 'project': project.name, 'status': i.status}
            printer.output_dict(output, sort=True, one_line=True)
            count += 1
        printer.output_dict({'header': 'Instance count', 'count': count})

def action_discard():
    for region in regions:
        novaclient = Nova(options.config, debug=options.debug, log=logger, region=region)
        glclient = Glance(options.config, debug=options.debug, log=logger, region=region)
        instances = novaclient.get_instances()
        count = 0
        for i in instances:
            image = glclient.get_image_by_id(i.image['id'])
            # Asume that hw_disk_bus == discard
            if 'hw_disk_bus' not in image:
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
