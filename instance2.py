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
from himlarcli.neutron import Neutron
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

def parse_addresses(text):
    """
    Parse a comma separated list of IPv4 and IPv6 addresses. Every
    address is validated and normalized, and duplicates are dropped, so
    one address written in two different IPv6 notations is looked up
    once rather than twice.
    """
    addresses = []
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        address = None
        try:
            address = ipaddress.ip_address(part)
        except ValueError:
            himutils.fatal(f'{part} is not a valid IPv4 or IPv6 address')
        if address is not None and address not in addresses:
            addresses.append(address)
    if not addresses:
        himutils.fatal(f'no address found in --ip {text}')
    return addresses

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

def match_any_ip(instance, addresses):
    """True if the instance holds any one of the given addresses."""
    return any(match_ip(instance, address) for address in addresses)

def instance_details(region, instance):
    """
    Collect the reportable fields of a single instance, in the order
    they should be presented. 'name' and 'region' come first because
    the compact output uses them as its header line.
    """
    project = get_object('project', instance.tenant_id)
    user = get_object('user', instance.user_id)
    ipv4, ipv6 = instance_addresses(instance)
    return {
        'name': instance.name,
        'region': region,
        'id': instance.id,
        'status': instance.status,
        'flavor': instance.flavor.get('original_name', 'unknown'),
        'created': short_date(instance.created),
        'project': project.name if project else f'(unknown id={instance.tenant_id})',
        'user': user.name if user else f'(unknown id={instance.user_id})',
        'ipv4': ', '.join(ipv4) if ipv4 else '(none)',
        'ipv6': ', '.join(ipv6) if ipv6 else '(none)',
    }

def short_date(created):
    """Turn nova's 2022-02-16T11:35:27Z into 2022-02-16 11:35:27."""
    try:
        return himutils.convert_date(created, '%Y-%m-%dT%H:%M:%SZ',
                                     '%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        logger.debug(f'=> unexpected date format {created}')
        return created

def output_instance(record):
    """Print one instance as a header line and a block of fields."""
    fields = {key: value for key, value in record.items()
              if key not in ('name', 'region')}
    printer.output_record(f"{record['name']} ({record['region']})", fields)

def output_instance_table(records):
    """Print instances as a table, one row per instance."""
    columns = ['id', 'name', 'region', 'status', 'flavor', 'ipv4', 'ipv6',
               'project', 'user']
    printer.output_records(header=[column.upper() for column in columns],
                           rows=[[record[column] for column in columns]
                                 for record in records],
                           sortby=columns.index('name'))

def find_instance_ids_by_ip(addresses):
    """
    Ask neutron which ports hold the given addresses and return a list
    of (region, instance id) pairs. This is the fast path for an IP
    search: neutron matches an address with an indexed, exact
    comparison, so it costs a couple of API calls per address and
    region instead of listing every instance in the region.

    Floating ips live outside a port's fixed_ips, so they are looked up
    separately, and only when an address is not a fixed ip anywhere.

    Pairs are deduplicated, so giving both the IPv4 and the IPv6
    address of one instance reports that instance once.

    Returns None if neutron could not be queried in some region, which
    tells the caller to fall back to scanning. An empty list means the
    lookups worked and none of the addresses are in use.
    """
    found = []
    seen = set()
    for region in sorted(regions):
        nc = himutils.get_client(Neutron, options, logger, region)
        for address in addresses:
            logger.debug(f'=> look up {address.compressed} in {region}')
            # Neutron stores addresses in canonical form, so always ask
            # with the compressed notation, not with what the user typed.
            ports = nc.get_ports(fixed_ips=f'ip_address={address.compressed}',
                                 fields=['device_id', 'device_owner'])
            if ports is None:
                return None
            if not ports:
                floatingips = nc.get_floatingips(floating_ip_address=address.compressed,
                                                 fields=['port_id'])
                if floatingips is None:
                    return None
                for floatingip in floatingips:
                    if not floatingip.get('port_id'):
                        continue
                    attached = nc.get_ports(id=floatingip['port_id'],
                                            fields=['device_id', 'device_owner'])
                    if attached is None:
                        return None
                    ports += attached
            for port in ports:
                owner = port.get('device_owner', '')
                if not owner.startswith('compute:'):
                    logger.debug(f'=> {address.compressed} in {region} is held by a '
                                 f"port owned by {owner or 'nobody'}, not an instance")
                    continue
                if not port.get('device_id'):
                    continue
                pair = (region, port['device_id'])
                if pair not in seen:
                    seen.add(pair)
                    found.append(pair)
    return found

def fetch_instances(instance_ids):
    """Yield (region, instance) for each (region, instance id) pair."""
    novaclients = {}
    for region, instance_id in instance_ids:
        if region not in novaclients:
            novaclients[region] = himutils.get_client(Nova, options, logger, region)
        instance = novaclients[region].get_by_id('server', instance_id)
        if not instance:
            himutils.error(f'port in {region} points at missing instance {instance_id}')
            continue
        yield region, instance

def scan_instances(addresses):
    """
    Yield (region, instance) for every instance, or for the instances
    holding any of the given addresses. This lists all instances in all
    selected regions, and is the slow path used when neutron cannot be
    queried. Each instance is yielded once however many of the
    addresses it holds.
    """
    for region, instance in iter_instances():
        if addresses and not match_any_ip(instance, addresses):
            continue
        yield region, instance

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

    --ip takes one address or several comma separated ones. An instance
    is reported once however many of the addresses belong to it, so
    passing both the IPv4 and the IPv6 address of a host is harmless.

    With --id-only the matching instance ids are printed bare, one per
    line, for feeding into a shell loop or xargs.

    An IP search is resolved through neutron, which knows the port that
    holds the address, so only the matching instances are fetched from
    nova. A name search has to list the instances of every selected
    region and match locally: nova's own name filter is a regex handed
    to its database, so translating a glob to it would behave differently
    from one deployment to the next.
    """
    if not options.name and not options.ip:
        himutils.fatal('search needs --name and/or --ip')
    addresses = parse_addresses(options.ip) if options.ip else []
    if options.name:
        case = 'ignoring case' if options.ignore_case else 'case sensitive'
        logger.debug(f'=> search for name matching {options.name} ({case})')

    if addresses:
        instance_ids = find_instance_ids_by_ip(addresses)
        if instance_ids is None:
            himutils.error('neutron lookup failed, falling back to '
                           'a full instance scan')
            candidates = scan_instances(addresses)
        else:
            candidates = fetch_instances(instance_ids)
    else:
        candidates = scan_instances([])

    records = [instance_details(region, instance)
               for region, instance in candidates
               if not options.name or match_name(instance, options.name,
                                                 options.ignore_case)]

    # --id-only exists to be piped, so it prints bare ids and ignores
    # both --format and the count footer
    if options.id_only:
        for record in records:
            print(record['id'])
        return

    # A single hit gets the full field block, several get a table. The
    # machine readable formats always get one full record per instance,
    # so that piping does not depend on how many instances matched.
    if options.format in ('json', 'csv'):
        for position, record in enumerate(records):
            # Printer writes a csv column header for a dict that has a
            # 'header' key, and it belongs above the first row only
            if options.format == 'csv' and position == 0:
                record = {'header': True, **record}
            printer.output_dict(record, sort=False)
    elif not records:
        pass
    elif options.format == 'table' or len(records) > 1:
        output_instance_table(records)
    else:
        output_instance(records[0])

    # The count is obvious when there is exactly one hit
    if len(records) != 1 and options.format in ('text', 'table'):
        printer.output_msg(f'{len(records)} instances found')

#---------------------------------------------------------------------
# Run local function with the same name as the action (Note: - => _)
#---------------------------------------------------------------------
action = locals().get(f"action_{options.action.replace('-', '_')}")
if not action:
    himutils.fatal(f'action_{options.action} not implemented')
action()
