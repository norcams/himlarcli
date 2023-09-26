#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
#from himlarcli.neutron import Neutron
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils
from himlarcli.state import State
from himlarcli.state import Instance
from himlarcli.color import Color

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
    if options.format == 'table':
        output = {}
        output['header'] = [
            'NAME',
            'HOSTS',
            'AVAILABILITY ZONE',
        ]
        output['align'] = [
            'l',
            'r',
            'l',
        ]
        output['sortby'] = 0
        counter = 0
        for region in regions:
            nova = utils.get_client(Nova, options, logger, region)
            aggregates = nova.get_aggregates(simple=False)

            for aggr in aggregates:
                output[counter] = [
                    Color.fg.ylw + aggr.name + Color.reset,
                    len(aggr.hosts),
                    Color.fg.CYN + aggr.metadata['availability_zone'] + Color.reset,
                ]
                counter += 1
        printer.output_dict(output, one_line=True)
    else:
        printer.output_dict({'header': 'Host aggregate (#hosts, name, az)'})
        for region in regions:
            nova = utils.get_client(Nova, options, logger, region)
            aggregates = nova.get_aggregates(simple=False)

            for aggr in aggregates:
                output = {
                    '2': aggr.name,
                    '3': aggr.metadata['availability_zone'],
                    '1': len(aggr.hosts)
                }
                printer.output_dict(output, one_line=True)

def action_show():
    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        aggregate = nova.get_aggregate(options.aggregate)
        if not aggregate:
            continue

        printer.output_dict({'header': 'Host aggregate in {}'.format(region)})
        printer.output_dict(aggregate.to_dict())

def action_orphan_instances():
    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        aggregate = nova.get_aggregate(options.aggregate)
        if not aggregate:
            printer.output_msg('no aggregate {} found in {}'.format(options.aggregate, region))
            continue
        instances = nova.get_instances(options.aggregate)
        printer.output_dict({'header': 'Instance list (id, host, status, flavor)'})
        status = dict({'total': 0})
        for i in instances:
            project = kc.get_by_id('project', i.tenant_id)
            if project:
                continue
            output = {
                '1': i.id,
                '2': nova.get_compute_host(i),
                #'3': i.name,
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

def action_instances():
    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        #neutron = utils.get_client(Neutron, options, logger)
        #network = neutron.list_networks()
        aggregate = nova.get_aggregate(options.aggregate)
        if not aggregate:
            printer.output_msg('no aggregate {} found in {}'.format(options.aggregate, region))
            continue
        instances = nova.get_instances(options.aggregate)
        printer.output_dict({'header': 'Instance list (id, host, status, flavor)'})
        status = dict({'total': 0})
        for i in instances:
            output = {
                '1': i.id,
                '2': nova.get_compute_host(i),
                #'3': i.name,
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

def action_stop_instance():
    msg = 'Remember to purge db with state.py first! Continue?'
    if not options.dry_run and not utils.confirm_action(msg):
        return
    state = utils.get_client(State, options, logger)

    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        instances = nova.get_instances(options.aggregate,
                                       nova.get_fqdn_host(options.host))
        for i in instances:
            instance_data = i.to_dict().copy()
            instance_data['region'] = region
            instance_data['aggregate'] = options.aggregate
            instance_data['host'] = getattr(i, 'OS-EXT-SRV-ATTR:host')
            instance_data['instance_id'] = i.id
            instance_data.pop('created', None) # not instance created, but db

            instance = state.get_first(Instance, instance_id=i.id)
            if instance is None: # add to db if not found
                instance = Instance.create(instance_data) #pylint: disable=E1101
                state.add(instance)

            nova.stop_instance(i, 'NREC maintenance in progress')
    state.close()

def action_start_instance():
    state = utils.get_client(State, options, logger)
    pre = state.log_prefix()
    for region in regions:
        nova = utils.get_client(Nova, options, logger, region)
        instances = state.get_all(Instance, region=region,
                                  aggregate=options.aggregate)

        for i in instances:
            if options.host and nova.get_fqdn_host(options.host) != i.host:
                logger.debug('%s instance host do not match %s', pre, i.host)
                continue
            logger.debug('%s instance found %s', pre, i.name)
            if i.status == 'ACTIVE':
                instance = nova.get_by_id('server', i.instance_id)
                nova.start_instance(instance, unlock=True)
    state.close()



# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
