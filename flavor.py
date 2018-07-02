#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from collections import OrderedDict

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc= Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()

# Flavors
flavors = himutils.load_config('config/flavors/%s.yaml' % options.flavor, logger)
if not flavors:
    himutils.sys_error('Could not find flavor config file config/flavors/%s.yaml'
                        % options.flavor)

def action_list():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        flavors = nc.get_flavors(filters=options.flavor)
        outputs = ['name', 'vcpus', 'ram', 'disk']
        header = 'flavors in %s (%s)' % (region, ', '.join(outputs))
        printer.output_dict({'header': header})
        for flavor in flavors:
            output = OrderedDict()
            for out in outputs:
                output[out] = getattr(flavor, out)
            printer.output_dict(objects=output, one_line=True, sort=False)

def action_update():
    public = flavors['public'] if 'public' in flavors else False
    properties = flavors['properties'] if 'properties' in flavors else None
    if (options.flavor not in flavors or
            not isinstance(flavors[options.flavor], dict)):
        himutils.sys_error('%s hash not found in config' % options.flavor)

    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        nc.set_dry_run(options.dry_run)
        for name, spec in sorted(flavors[options.flavor].iteritems()):
            nc.update_flavor(name=name, spec=spec,
                             properties=properties, public=public)

def action_purge():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        nc.set_dry_run(options.dry_run)
        print 'Purge %s flavors in %s' % (options.flavor, region)
        nc.purge_flavors(options.flavor, flavors)

def action_grant():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        nc.set_dry_run(options.dry_run)
        update_access(nc, 'grant')

def action_revoke():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger)
        nc.set_dry_run(options.dry_run)
        update_access(nc, 'grant')

def update_access(nc, action):
    public = flavors['public'] if 'public' in flavors else False
    if 'public' in flavors and flavors['public']:
        himutils.sys_error('grant or revoke will not work on public flavors!')
    project = kc.get_project_by_name(options.project)
    if not project:
        himutils.sys_error('project not found %s' % project)
    print "%s access to %s for %s" % (action, options.flavor, options.project)
    nc.update_flavor_access(filters=options.flavor,
                            project_id=project.id,
                            action=action)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
