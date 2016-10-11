#!/usr/bin/env python
import utils
import sys
#from himlarcli.nova import Nova
from himlarcli.keystone import Keystone
#import himlarcli.foremanclient as foreman
from himlarcli.foremanclient import Client
from himlarcli import utils as himutils

desc = 'Setup compute resources and profiles'
options = utils.get_options(desc, hosts=False, dry_run=True)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()
domain = keystone.get_config('openstack', 'domain')

client = Client(options.config, options.debug, log=logger)
foreman = client.get_client()

# Add compute resources
resource_config = himutils.load_config('config/compute_resources.yaml')
if keystone.region not in resource_config:
    num_resources = resource_config['default']['num_resources']
else:
    num_resources = resource_config[keystone.region]['num_resources']
logger.debug("=> number of compute resources for %s: %s" % (keystone.region, num_resources))
resources = foreman.index_computeresources()
found_resources = dict({})
for r in resources['results']:
    found_resources[r['name']] = r['id']

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
            result = foreman.create_computeresources(resource)
            found_resources[name] = result['id']
    else:
        logger.debug('=> update compute resource %s' % name)
        if not options.dry_run:
            result = foreman.update_computeresources(found_resources[name], resource)


# Compute profile
profile_config = himutils.load_config('config/compute_profiles.yaml')
if keystone.region not in profile_config:
    compute_attribute = profile_config['default']
else:
    compute_attribute = profile_config[keystone.region]

for x in range(1,4):
    profile = foreman.show_computeprofiles(x)
    for r in found_resources:
        if not profile['compute_attributes']:
            if not options.dry_run:
                result = foreman.create_computeattributes(
                        compute_profile_id=x,
                        compute_resource_id=found_resources[r],
                        compute_attribute=compute_attribute[x])
                logger.debug("=> create result %s" % result)
            else:
                logger.debug('=> dryrun %s: %s' % (profile['name'], compute_attribute[x]))

        for attr in profile['compute_attributes']:
            if r == attr['compute_resource_name']:
                if attr['vm_attrs'] == compute_attribute[x]['vm_attrs']:
                    logger.debug("=> %s: no change for %s" % (profile['name'], r))
                    continue
                if not options.dry_run:
                    result = foreman.update_computeattributes(
                            compute_profile_id=x,
                            compute_resource_id=found_resources[r],
                            id=attr['id'],
                            compute_attribute=compute_attribute[x])
                    logger.debug("=> update result %s" % result)
                else:
                    logger.debug("=> dryrun %s: %s" % (profile['name'], compute_attribute[x]))
