#!/usr/bin/env python

from himlarcli import tests
tests.is_virtual_env()

from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as himutils
from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
from himlarcli.statsdclient import StatsdClient

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()
statsd = StatsdClient(options.config, debug=options.debug, log=logger)
statsd.set_dry_run(options.dry_run)

# Region
if hasattr(options, 'region'):
    regions = kc.find_regions(region_name=options.region)
else:
    regions = kc.find_regions()


def action_compute():
    stats = {}
    for region in regions:
        drop_az = ['iaas-team-only', f'{region}-legacy-1']
        metrics = ['vcpus', 'vcpus_used', 'running_vms', 'memory_mb_used',
                   'memory_mb', 'local_gb']
        nc = Nova(options.config, debug=options.debug, region=region, log=logger)
        aggregates = nc.get_aggregates(False)
        for a in aggregates:
            a_name = f'{region}-{a.name}'
            stats[a_name] = {}
            if a.availability_zone in drop_az:
                continue
            hosts = nc.get_aggregate_hosts(a.name, True)
            for host in hosts:
                #print host.to_dict()
                for metric in metrics:
                    logger.debug('=> %s %s=%s', host.hypervisor_hostname,
                                 metric, getattr(host, metric))
                    stats[a_name][metric] = int(getattr(host, metric) +
                                                stats[a_name].get(metric, 0))
    statsd.gauge_dict('compute', stats)
    if not options.quiet:
        for name, stat in stats.items():
            printer.output_dict({'header': name})
            printer.output_dict(stat)

def action_legacy():
    projects_count = kc.get_project_count('dataporten')
    users_count = kc.get_user_count('dataporten')

    stats = {}
    stats['users'] = {}
    stats['projects'] = {}
    stats['instances'] = {}
    stats['instances']['total'] = {'count': 0, 'error': 0}

    for region in regions:
        logger.debug(f'=> count region {region}')

        # Projects and users (this will be the same for all regions)
        stats['projects'][region] = {}
        stats['projects']['total'] = {}
        stats['projects'][region]['count'] = projects_count
        stats['projects']['total']['count'] = projects_count
        stats['users'][region] = {}
        stats['users']['total'] = {}
        stats['users'][region]['count'] = users_count
        stats['users']['total']['count'] = users_count

        # Instances
        novaclient = Nova(options.config, debug=options.debug,
                          region=region, log=logger)
        novastats = novaclient.get_stats()
        stats['instances'][region] = {}
        stats['instances'][region]['count'] = novastats['count']
        stats['instances'][region]['error'] = novastats['error']
        stats['instances']['total']['count'] += novastats['count']
        stats['instances']['total']['error'] += novastats['error']

    for t, s in stats.items():
        for r, d in s.items():
            name = f'{r}.{t}'
            count = d['count']
            if not options.quiet:
                print(f'{name} = {count}')
            statsd.gauge(name, count)
            if 'error' in d:
                name = f'{r}.instance_errors'
                if not options.quiet:
                    print(f"{name} = {d['error']}")
                statsd.gauge(name, d['error'])

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error(f"Function action_{options.action}() not implemented")
action()
