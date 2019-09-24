#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.cinder import Cinder
from himlarcli.nova import Nova
from himlarcli.neutron import Neutron
from himlarcli.keystone import Keystone
from himlarcli.state import State
from himlarcli.state import Quota
from himlarcli.state import Keypair

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
state = State(options.config, debug=options.debug, log=logger)
state.set_dry_run(options.dry_run)

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()

def action_save():
    if options.resource == 'quota':
        projects = kc.get_all_projects()
        for region in regions:
            nova = himutils.get_client(Nova, options, logger, region)
            cinder = himutils.get_client(Cinder, options, logger, region)
            neutron = himutils.get_client(Neutron, options, logger, region)
            for project in projects:
                quotas = nova.get_quota(project.id).copy()
                quotas.update(cinder.get_quota(project.id))
                quotas.update(neutron.get_quota(project.id))
                quotas['project_id'] = project.id
                quotas['region'] = region
                q = state.get_first(Quota, project_id=project.id, region=region)
                if q is not None:
                    state.update(q, quotas)
                else:
                    quota = Quota.create(quotas) # pylint: disable=E1101
                    state.add(quota)
    elif options.resource == 'keypair':
        users = kc.get_users()
        for region in regions:
            nova = himutils.get_client(Nova, options, logger, region)
            for user in users:
                keypairs = nova.get_keypairs(user_id=user.id)
                for key in keypairs:
                    keypair = {
                        'user_id': user.id,
                        'name': key.name,
                        'public_key': key.public_key,
                        'region': region,
                        'type': key.type
                    }
                    k = state.get_first(Keypair, region=region, user_id=user.id, name=key.name)
                    logger.debug('=> key %s for user %s', key.name, user.name)
                    if k is not None:
                        state.update(k, keypair)
                    else:
                        state.add(Keypair.create(keypair)) # pylint: disable=E1101

def action_compare():
    if options.resource == 'quota':
        projects = kc.get_all_projects()
        for region in regions:
            printer.output_dict({'header': 'quota miss match found in %s' % region})
            nova = himutils.get_client(Nova, options, logger, region)
            cinder = himutils.get_client(Cinder, options, logger, region)
            neutron = himutils.get_client(Neutron, options, logger, region)
            for project in projects:
                quotas = nova.get_quota(project.id).copy()
                quotas.update(cinder.get_quota(project.id))
                quotas.update(neutron.get_quota(project.id))
                quotas['project_id'] = project.id
                quotas['region'] = region
                q = state.get_first(Quota, project_id=project.id, region=region)
                if q is None:
                    print 'could not find saved quota for %s' % project.name
                    continue
                miss_match = q.compare(quotas)
                if miss_match:
                    output = {
                        '1': project.name,
                        '2': miss_match
                    }
                    printer.output_dict(output, one_line=True)
    elif options.resource == 'keypair':
        users = kc.get_users()
        for region in regions:
            printer.output_dict({'header': 'ssh keys miss match found in %s' % region})
            nova = himutils.get_client(Nova, options, logger, region)
            for user in users:
                keypairs = list()
                temp = nova.get_keypairs(user_id=user.id)
                for k in temp:
                    keypairs.append(k)
                saved_keys = state.get_all(Keypair, user_id=user.id)
                if len(keypairs) != len(saved_keys):
                    output = {
                        '1': user.name,
                        '2': len(keypairs),
                        '3': len(saved_keys)
                    }
                    printer.output_dict(output, one_line=True)

def action_replace():
    print 'not implemented'

def action_purge():
    state.purge(options.resource)

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
