#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from collections import OrderedDict
import glob

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()

def action_list():
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        flavors = nc.get_flavors(class_filter=options.flavor)
        outputs = ['name', 'vcpus', 'ram', 'disk']
        header = 'flavors in %s (%s)' % (region, ', '.join(outputs))
        printer.output_dict({'header': header})
        for flavor in flavors:
            output = OrderedDict()
            for out in outputs:
                output[out] = getattr(flavor, out)
            printer.output_dict(objects=output, one_line=True, sort=False)

def action_instances():
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        flavors = nc.get_flavors(class_filter=options.flavor)

        printer.output_dict({'header': 'Instance list %s (id, name, flavor)' % region})
        status = dict({'total': 0})
        for flavor in flavors:
            search_opts = dict(all_tenants=1, flavor=flavor.id)
            instances = nc.get_all_instances(search_opts=search_opts)

            for i in instances:
                output = {
                    '1': i.id,
                    '3': i.name,
                    '4': i.status,
                    #'2': i.updated,
                    #'6'': getattr(i, 'OS-EXT-SRV-ATTR:instance_name'),
                    '5': i.flavor['original_name']
                }
                printer.output_dict(output, sort=True, one_line=True)
                status['total'] += 1
                status[str(i.status).lower()] = status.get(str(i.status).lower(), 0) + 1
        printer.output_dict({'header': 'Counts'})
        printer.output_dict(status)

def action_update():
    question = ("This will delete the flavor and recreate it for all other "
                "changes than properties. Check project access after. Continue?")
    if not himutils.confirm_action(question):
        return

    for region in regions:
        flavors = get_flavor_config(region)
        public = flavors['public'] if 'public' in flavors else False
        properties = flavors['properties'] if 'properties' in flavors else dict()
        if not properties or not properties.get('aggregate_instance_extra_specs:type', None):
            properties['aggregate_instance_extra_specs:type'] = 's== standard'
        if (options.flavor not in flavors or
                not isinstance(flavors[options.flavor], dict)):
            himutils.sys_error('%s hash not found in config' % options.flavor)

        nc = Nova(options.config, debug=options.debug, log=logger, region=region)
        nc.set_dry_run(options.dry_run)
        for name, spec in sorted(flavors[options.flavor].iteritems()):
            # Hack to override properties per flavor
            flavor_properties = properties.copy()
            if 'properties' in spec:
                for p_name, prop in spec['properties'].iteritems():
                    flavor_properties[p_name] = prop
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
            nc.update_flavor_access(class_filter=options.flavor,
                                    project_id=project,
                                    action='grant')

def action_purge():
    q = 'Purge flavors from class {} in region(s) {}'.format(options.flavor, ','.join(regions))
    if not himutils.confirm_action(q):
        return
    for region in regions:
        flavors = get_flavor_config(region)
        nc = himutils.get_client(Nova, options, logger, region)
        nc.debug_log('Start purge of flavor class {} from region {}'.format(options.flavor, region))
        result = nc.purge_flavors(class_filter=options.flavor, flavors=flavors)
        if result:
            printer.output_msg('Purged flavors of class {} from region {}'
                               .format(options.flavor, region))
        else:
            printer.output_msg('Nothing to purge from region {}'.format(region))

def action_delete():
    q = 'Delete flavor class {} in region(s) {}'.format(options.flavor, ','.join(regions))
    if not himutils.confirm_action(q):
        return
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        nc.debug_log('Start delete all {} from region {}'.format(options.flavor, region))
        result = nc.delete_flavors(class_filter=options.flavor)
        if result:
            printer.output_msg('Deleted all {} from region {}'.format(options.flavor, region))
        else:
            printer.output_msg('Nothing to delete from region {}'.format(region))

def action_grant():
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        result = update_access(nc, 'grant', region)
        if result:
            printer.output_msg("Grant access to {} for {} in {}"
                               .format(options.flavor, options.project, region))

def action_revoke():
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
        result = update_access(nc, 'revoke', region)
        if result:
            printer.output_msg("Revoke access to {} for {} in {}"
                               .format(options.flavor, options.project, region))

def action_list_access():
    for region in regions:
        nc = himutils.get_client(Nova, options, logger, region)
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

def action_available_flavors():
    path = '/opt/himlarcli/config/flavors/*.yaml'
    files = glob.glob(path)
    for file in files:
        f = open(file, 'r')
        print(file)
        print(f.readlines()[1])
        f.close()

def get_flavor_config(region):
    # First look for region version of flavor config, then the default one
    if himutils.file_exists('config/flavors/%s-%s.yaml' % (options.flavor, region)):
        configfile = 'config/flavors/%s-%s.yaml' % (options.flavor, region)
    else:
        configfile = 'config/flavors/%s.yaml' % (options.flavor)
    kc.debug_log('use flavor config from %s' % configfile)
    flavors = himutils.load_config(configfile)
    if not flavors:
        himutils.sys_error('Could not find flavor config file config/flavors/%s.yaml'
                           % options.flavor)
    return flavors

def update_access(nc, access_action, region):
    flavors = get_flavor_config(region)
    if options.flavor in flavors and not flavors[options.flavor]:
        return False
    if 'public' in flavors and flavors['public']:
        himutils.sys_error('grant or revoke will not work on public flavors!')
    project = kc.get_project_by_name(options.project)
    if not project:
        himutils.sys_error('project not found %s' % project)
    result = nc.update_flavor_access(class_filter=options.flavor,
                                     project_id=project.id,
                                     action=access_action)
    if not result:
        himutils.sys_error('Update access for {} failed. Check debug log'
                           .format(options.flavor), 0)
        return False
    return True

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
