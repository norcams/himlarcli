#!/usr/bin/env python
import utils
from himlarcli.keystone import Keystone
from himlarcli.foremanclient import ForemanClient
from himlarcli import utils as himutils

# Fix foreman functions and logger not-callable
# pylint: disable=E1101,E1102

desc = 'Setup compute resources and profiles'
options = utils.get_options(desc, hosts=False, dry_run=True)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()
domain = keystone.get_config('openstack', 'domain')

foreman = ForemanClient(options.config, options.debug, log=logger)

# Add compute resources
resource_config = himutils.load_config('config/compute_resources.yaml')
if keystone.region not in resource_config:
    num_resources = resource_config['default']['num_resources']
else:
    num_resources = resource_config[keystone.region]['num_resources']
logger.debug("=> number of compute resources for %s: %s" % (keystone.region, num_resources))
found_resources = foreman.get_compute_resources()

for x in range(1, (num_resources+1)):
    name = '%s-controller-0%s' % (keystone.region, x)
    resource = dict()
    resource['name'] = name
    resource['provider'] = 'Libvirt'
    resource['set_console_password'] = 0
    resource['url'] = 'qemu+tcp://%s.%s:16509/system' % (name, domain)
    if name not in found_resources:
        logger.debug('=> add new compute resource %s' % name)
        if not options.dry_run:
            result = foreman.create_compute_resources(resource)
            found_resources[name] = result['id']
    else:
        logger.debug('=> update compute resource %s' % name)
        if not options.dry_run:
            result = foreman.update_compute_resources(found_resources[name], resource)

# Compute profile
profile_config = himutils.load_config('config/compute_profiles.yaml')
if keystone.region not in profile_config:
    compute_attribute = profile_config['default']
else:
    compute_attribute = profile_config[keystone.region]

for x in range(1, 4):
    profile = foreman.show_compute_profile(x)
    for r in found_resources:
        found_profile = None
        for attr in profile['compute_attributes']:
            if r == attr['compute_resource_name']:
                found_profile = attr
        if not found_profile:
            if not options.dry_run:
                result = foreman.create_compute_attributes(
                    compute_profile_id=x,
                    compute_resource_id=found_resources[r],
                    compute_attribute=compute_attribute[x])
                logger.debug("=> create result %s" % result)
            else:
                logger.debug('=> dryrun %s(%s): %s' % (r, profile['name'], compute_attribute[x]))
        else:
            attr = found_profile
            if r == attr['compute_resource_name']:
                if attr['vm_attrs'] == compute_attribute[x]['vm_attrs']:
                    logger.debug("=> %s: no change for %s" % (profile['name'], r))
                    continue
                if not options.dry_run:
                    result = foreman.update_compute_attributes(
                        compute_profile_id=x,
                        compute_resource_id=found_resources[r],
                        id=attr['id'],
                        compute_attribute=compute_attribute[x])
                    logger.debug("=> update result %s" % result)
                else:
                    logger.debug("=> dryrun %s(%s): %s" % (r, profile['name'], compute_attribute[x]))
