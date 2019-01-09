#!/usr/bin/env python
import utils
from himlarcli.keystone import Keystone
from himlarcli.foremanclient import ForemanClient
from himlarcli import utils as himutils

# Fix foreman functions and logger not-callable
# pylint: disable=E1101,E1102

desc = 'Setup compute resources and profiles'
options = utils.get_options(desc, hosts=False)
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
        result = foreman.create_compute_resources(resource)
        found_resources[name] = result['id']
    else:
        logger.debug('=> update compute resource %s' % name)
        result = foreman.update_compute_resources(found_resources[name], resource)

# Compute profile
profile_config = himutils.load_config('config/compute_profiles.yaml')
if keystone.region not in profile_config:
    profiles = profile_config['default']
else:
    profiles = profile_config[keystone.region]

found_profiles = foreman.get_compute_profiles()

verified_profiles = list()

if found_profiles:
    for found_profile in found_profiles.keys():
        if found_profile not in profiles:
            # We only want profiles defined in config/compute_profiles.yaml
            logger.debug("=> deleting profile %s" % found_profile)
            foreman.delete_compute_profile(found_profiles[found_profile])
        else:
            verified_profiles.append(found_profile)

for profile_name in profiles.keys():
    if profile_name not in verified_profiles:
        compute_profile = {'compute_profile': {'name': profile_name}}
        profile_result = foreman.create_compute_profile(compute_profile)
        logger.debug("=> create profile result %s" % profile_result)
        for r in found_resources:
            attr_result = foreman.create_compute_attributes(
                profile_result['id'],
                found_resources[r],
                profiles[profile_name])
            logger.debug("=> create attributes result %s" % attr_result)
    else:
        ext_profile = foreman.show_compute_profile(found_profiles[profile_name])
        for attr in ext_profile['compute_attributes']:
            name = attr['compute_profile_name']
            if attr['vm_attrs'] == profiles[name]['vm_attrs']:
                logger.debug("=> no change for %s" % name)
            else:
                for r in found_resources:
                    result = foreman.update_compute_attributes(
                        attr['compute_profile_id'],
                        found_resources[r],
                        attr['id'],
                        profiles[name])
                    logger.debug("=> update result %s" % result)
