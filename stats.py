#!/usr/bin/env python

from himlarcli import tests as tests
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
    stats = dict()
    for region in regions:
        drop_az = ['iaas-team-only', '%s-legacy-1' % region]
        metrics = ['vcpus', 'vcpus_used', 'running_vms', 'memory_mb_used',
                   'memory_mb', 'local_gb']
        nc = Nova(options.config, debug=options.debug, region=region, log=logger)
        aggregates = nc.get_aggregates(False)
        for a in aggregates:
            stats[a.name] = dict()
            if a.availability_zone in drop_az:
                continue
            hosts = nc.get_aggregate_hosts(a.name, True)
            for host in hosts:
                print host.to_dict()
                for metric in metrics:
                    logger.debug('=> %s %s=%s', host.hypervisor_hostname, metric, getattr(host, metric))
                    stats[a.name][metric] = int(getattr(host, metric) +
                                                stats[a.name].get(metric, 0))

        # azs = nc.get_availability_zones()

        # zone_hosts = dict()
        # # Availablity zones
        # for az in azs:
        #     if ('iaas-team-only' in az.zoneName or
        #             region not in az.zoneName or not az.hosts):
        #         continue
        #     for host in az.hosts.iterkeys():
        #         zone_hosts[host] = az.zoneName
        #     stats[az.zoneName] = dict()
        #     for metric in metrics:
        #         stats[az.zoneName][metric] = 0
        # # Hypervisor hosts
        # hosts = nc.get_hosts()
        # for host in hosts:
        #     if not host.hypervisor_hostname in zone_hosts:
        #         himutils.sys_error('host %s not enabled or in valid az'
        #                            % host.hypervisor_hostname, 0)
        #         continue
        #     az = zone_hosts[host.hypervisor_hostname]
        #     for metric in metrics:
        #         logger.debug('=> %s %s=%s', host.hypervisor_hostname, metric, getattr(host, metric))
        #         stats[az][metric] = int(getattr(host, metric) + stats[az][metric])
    statsd.gauge_dict('compute', stats)
    if not options.quiet:
        for name, stat in stats.iteritems():
            printer.output_dict({'header': name})
            printer.output_dict(stat)

def action_legacy():
    projects_count = kc.get_project_count('dataporten')
    users_count = kc.get_user_count('dataporten')

    stats = dict()
    stats['users'] = {}
    stats['projects'] = {}
    stats['instances'] = {}
    stats['instances']['total'] = {'count': 0, 'error': 0}

    for region in regions:
        logger.debug('=> count region %s' % region)

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
        novaclient = Nova(options.config, debug=options.debug, region=region, log=logger)
        novastats = novaclient.get_stats()
        stats['instances'][region] = {}
        stats['instances'][region]['count'] = novastats['count']
        stats['instances'][region]['error'] = novastats['error']
        stats['instances']['total']['count'] += novastats['count']
        stats['instances']['total']['error'] += novastats['error']

    for t, s in stats.iteritems():
        for r, d in s.iteritems():
            name = '%s.%s' % (r, t)
            count = d['count']
            if not options.quiet:
                print '%s = %s' % (name, count)
            statsd.gauge(name, count)
            if 'error' in d:
                name = '%s.instance_errors' % (r)
                if not options.quiet:
                    print '%s = %s' % (name, d['error'])
                statsd.gauge(name, d['error'])

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
