#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.glance import Glance
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

region = kc.get_region()

def action_list():

    nc = utils.get_client(Nova, options, logger, region)
    gc = utils.get_client(Glance, options, logger, region)

    instances = utils.load_file('/tmp/q35-{}.txt'.format(region))

    for i, line in enumerate(instances):
        if 'osl-compute-' in line:
            continue
        if options.limit and i > options.limit:
            break
        instance = nc.get_by_id('server', line.split(' ')[-1])
        image = gc.get_image_by_id(instance.image['id'])
        image_name = image.tags
        if 'gold' in image_name:
            image_name.remove('gold')

        output = {
            '0': instance.id,
            '1': instance.name,
            '2': image_name[0]
        }
        printer.output_dict(output, sort=False, one_line=True)


# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
