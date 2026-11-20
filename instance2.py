#!/usr/bin/env python
"""
Instance statistics for the NREC cloud.

Counts instances across all (or one) region and groups them by project
type, by the email domain of the owning user, or by the organization
derived from that domain. The 'user' action lists every instance owned
by a single user, grouped by project, and the 'search' action looks up
instances by name glob and/or IP address.

Working name for the next generation of instance.py.
"""

import fnmatch
import ipaddress
from collections import Counter
from functools import lru_cache

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
regions = himutils.get_regions(options, kc)

# Project types reported by the 'project' action. Instances in a project
# with any other type are counted in the total only, and a warning is
# emitted so the list below can be updated.
PROJECT_TYPES = ['admin', 'demo', 'education', 'hpc', 'personal', 'research', 'test']

#---------------------------------------------------------------------
# Helper functions
#---------------------------------------------------------------------
@lru_cache(maxsize=None)
def get_object(obj_type, obj_id):
    """
    Memoized keystone lookup by id. Many instances share the same
    project and user, so without the cache this is by far the most
    expensive part of the stats actions.
    """
    return kc.get_by_id(obj_type, obj_id)

def iter_instances():
    """Yield (region, instance) for every instance in the selected regions."""
    for region in sorted(regions):
        logger.debug(f'=> count region {region}')
        nc = himutils.get_client(Nova, options, logger, region)
        for instance in nc.get_all_instances():
            yield region, instance

def count_instances(classify):
    """
    Count all instances, grouped by the key returned by classify(instance).
    A classifier returning None counts towards the total only.
    """
    stats = Counter()
    total = 0
    for _region, instance in iter_instances():
        total += 1
        key = classify(instance)
        if key:
            stats[key] += 1
    stats['total'] = total
    return stats

def output_stats(stats, subject):
    """Print stats as either an instance count or a percentage of the total."""
    total = stats.get('total', 0)
    if options.output == 'count':
        result = dict(stats)
        result['header'] = f'Number of instances grouped by {subject}:'
    elif total > 0:
        result = {key: (value / total) * 100 for key, value in stats.items()}
        result['header'] = f'Percent of instances grouped by {subject}:'
    else:
        result = {'header': f'Percent of instances grouped by {subject}:'}
    printer.output_dict(result)

def classify_project_type(instance):
    """
    Map an instance to the type of the project that owns it. Diagnostics
    go to stderr (himutils.error), never stdout, so that --format json
    and --format csv stay machine readable.
    """
    project = get_object('project', instance.tenant_id)
    if not project:
        himutils.error(f'missing project id={instance.tenant_id} '
                       f'for instance {instance.name} ({instance.id})')
        return None
    if hasattr(project, 'course'):
        return 'education'
    if '@' in project.name:
        return 'personal'
    project_type = getattr(project, 'type', None)
    if not project_type:
        return 'admin'
    if project_type not in PROJECT_TYPES:
        himutils.error(f'unknown project type {project_type} for {project.name}')
        return None
    return project_type

def classify_email_domain(instance):
    """Map an instance to the email domain of the user that created it."""
    user = get_object('user', instance.user_id)
    if not user:
        logger.debug(f'=> unknown user for {instance.name} (id={instance.id})')
        return 'unknown'
    if '@' not in user.name:
        return 'sysuser'
    return user.name.split('@')[1]

def classify_organization(instance):
    """Map an instance to the organization of the user that created it."""
    domain = classify_email_domain(instance)
    if domain in ('unknown', 'sysuser'):
        return domain
    labels = domain.split('.')
    return labels[-2] if len(labels) > 1 else 'unknown'

def instance_addresses(instance):
    """
    Return the (ipv4, ipv6) address strings of an instance. Both fixed
    and floating addresses are included, for every attached network.
    """
    ipv4 = []
    ipv6 = []
    for interfaces in instance.addresses.values():
        for interface in interfaces:
            if interface.get('version') == 4:
                ipv4.append(interface['addr'])
            elif interface.get('version') == 6:
                ipv6.append(interface['addr'])
    return ipv4, ipv6

def match_name(instance, pattern, ignore_case=False):
    """
    Match an instance name against a shell style glob (* ? [seq]). The
    glob has to cover the whole name, so use '*foo*' to search for a
    substring. Matching is case sensitive unless ignore_case is set.
    """
    if ignore_case:
        return fnmatch.fnmatchcase(instance.name.lower(), pattern.lower())
    return fnmatch.fnmatchcase(instance.name, pattern)

def match_ip(instance, address):
    """
    True if any address of the instance equals the given address, which
    is an ipaddress.IPv4Address or IPv6Address. Comparing parsed objects
    rather than strings makes this immune to IPv6 notation differences,
    so 2001:db8::1 also matches 2001:0DB8:0:0:0:0:0:1.
    """
    for interfaces in instance.addresses.values():
        for interface in interfaces:
            try:
                if ipaddress.ip_address(interface['addr']) == address:
                    return True
            except ValueError:
                logger.debug(f"=> unparsable address {interface['addr']} "
                             f'for instance {instance.name} ({instance.id})')
    return False

def instance_details(region, instance):
    """Collect the reportable fields of a single instance."""
    project = get_object('project', instance.tenant_id)
    user = get_object('user', instance.user_id)
    ipv4, ipv6 = instance_addresses(instance)
    return {
        'header': f'{instance.name} ({region})',
        'id': instance.id,
        'status': instance.status,
        'region': region,
        'project': project.name if project else f'(unknown id={instance.tenant_id})',
        'user': user.name if user else f'(unknown id={instance.user_id})',
        'flavor': instance.flavor.get('original_name', 'unknown'),
        'created': instance.created,
        'ipv4': ', '.join(ipv4) if ipv4 else '(none)',
        'ipv6': ', '.join(ipv6) if ipv6 else '(none)',
    }

#---------------------------------------------------------------------
# Action functions
#---------------------------------------------------------------------
def action_project():
    stats = count_instances(classify_project_type)
    for project_type in PROJECT_TYPES:
        stats.setdefault(project_type, 0)
    output_stats(stats, 'project type')

def action_users():
    output_stats(count_instances(classify_email_domain), 'user email domain')

def action_org():
    output_stats(count_instances(classify_organization), 'user organization')

def action_user():
    if not kc.is_valid_user(email=options.email):
        himutils.fatal(f'{options.email} is not a valid user. '
                       'Please check your spelling and case.')
    user_objects = kc.get_user_objects(email=options.email, domain=options.domain)
    novaclients = {region: himutils.get_client(Nova, options, logger, region)
                   for region in sorted(regions)}
    total = 0
    for project in user_objects['projects']:
        instances = [f'{instance.name} ({region})'
                     for region, nc in novaclients.items()
                     for instance in nc.get_project_instances(project.id)]
        total += len(instances)
        printer.output_dict({
            'header': f"{project.name} (type={getattr(project, 'type', 'unknown')})",
            'instances': instances if instances else ['(none)'],
        })
    printer.output_dict({
        'header': f'Instances owned by {options.email}',
        'total': total,
    })

def action_search():
    """
    Search for instances by name glob and/or IP address. Both filters
    may be combined, in which case an instance has to match both.

    Filtering is done locally on a full instance listing per region
    rather than through nova's own 'name'/'ip'/'ip6' search options.
    That costs one listing per region, but keeps glob semantics the same
    everywhere instead of depending on the regex dialect of nova's
    database, and it also finds floating IPs, which nova's ip filter
    does not match.
    """
    if not options.name and not options.ip:
        himutils.fatal('search needs --name and/or --ip')
    address = None
    if options.ip:
        try:
            address = ipaddress.ip_address(options.ip)
        except ValueError:
            himutils.fatal(f'{options.ip} is not a valid IPv4 or IPv6 address')
        logger.debug(f'=> search for IPv{address.version} address {address.compressed}')
    if options.name:
        case = 'ignoring case' if options.ignore_case else 'case sensitive'
        logger.debug(f'=> search for name matching {options.name} ({case})')

    found = 0
    for region, instance in iter_instances():
        if options.name and not match_name(instance, options.name,
                                           options.ignore_case):
            continue
        if address and not match_ip(instance, address):
            continue
        found += 1
        printer.output_dict(instance_details(region, instance))
    printer.output_dict({'header': f'Instances found: {found}'})

#---------------------------------------------------------------------
# Run local function with the same name as the action (Note: - => _)
#---------------------------------------------------------------------
action = locals().get(f"action_{options.action.replace('-', '_')}")
if not action:
    himutils.fatal(f'action_{options.action} not implemented')
action()
