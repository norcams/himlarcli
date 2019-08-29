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
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
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
    question = ("This will delete the flavor and recreate it for all other "
        "changes than properties. Check project access after. Continue?")
    if not himutils.confirm_action(question):
        return
    public = flavors['public'] if 'public' in flavors else False
    properties = flavors['properties'] if 'properties' in flavors else None
    if not properties.get('aggregate_instance_extra_specs:type', None):
        properties['aggregate_instance_extra_specs:type'] = 's== standard'
    if (options.flavor not in flavors or
            not isinstance(flavors[options.flavor], dict)):
        himutils.sys_error('%s hash not found in config' % options.flavor)

    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        nc.set_dry_run(options.dry_run)
        for name, spec in sorted(flavors[options.flavor].iteritems()):
            # Hack to override properties per flavor
            flavor_properties = properties.copy()
            if 'properties' in spec:
                for p_name, property in spec['properties'].iteritems():
                    flavor_properties[p_name] = property
                del spec['properties']
            nc.update_flavor(name=name, spec=spec,
                             properties=flavor_properties, public=public)
        # Update access
        access = nc.get_flavor_access(filters=options.flavor)
        all_projects = set()
        for name, projects in access.iteritems():
            for project_id in projects:
                all_projects.add(project_id.tenant_id)
        for project in all_projects:
            nc.update_flavor_access(filters=options.flavor,
                                    project_id=project,
                                    action='grant')

def action_purge():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        nc.set_dry_run(options.dry_run)
        print 'Purge %s flavors in %s' % (options.flavor, region)
        nc.purge_flavors(options.flavor, flavors)

def action_grant():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        nc.set_dry_run(options.dry_run)
        update_access(nc, 'grant')
        print "Grant access to %s for %s in %s" % (options.flavor,
            options.project, region)

def action_revoke():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        nc.set_dry_run(options.dry_run)
        update_access(nc, 'revoke')
        print "Revoke access to %s for %s in %s" % (options.flavor,
            options.project, region)

def action_list_access():
    for region in regions:
        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        nc.set_dry_run(options.dry_run)
        access = nc.get_flavor_access(filters=options.flavor)
        header = 'access to %s flavor in %s' % (options.flavor, region)
        printer.output_dict({'header': header})
        output = dict()
        for name, projects in access.iteritems():
            output[name] = list()
            for project_id in projects:
                project = kc.get_by_id('project', project_id.tenant_id)
                if project:
                    output[name].append(project.name)
                else:
                    himutils.sys_error('project not found %s' % project_id.tenant_id, 0)
                    continue
        printer.output_dict(output)

def update_access(nc, action):
    public = flavors['public'] if 'public' in flavors else False
    if 'public' in flavors and flavors['public']:
        himutils.sys_error('grant or revoke will not work on public flavors!')
    project = kc.get_project_by_name(options.project)
    if not project:
        himutils.sys_error('project not found %s' % project)
    nc.update_flavor_access(filters=options.flavor,
                            project_id=project.id,
                            action=action)

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
