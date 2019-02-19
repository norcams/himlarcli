#!/usr/bin/env python
import utils
from himlarcli.keystone import Keystone
from himlarcli.foremanclient import ForemanClient
from himlarcli import utils as himutils

# Fix foreman functions and logger not-callable
# pylint: disable=E1101,E1102

desc = 'Setup Foreman for himlar'
options = utils.get_options(desc, hosts=False)
keystone = Keystone(options.config, debug=options.debug)
logger = keystone.get_logger()
domain = keystone.get_config('openstack', 'domain')

foreman = ForemanClient(options.config, options.debug, log=logger)
client = foreman.get_client()

# create foreman domain based on config
# get domain id

# get smart proxy id for tftp

# create subnet
# mgmt network + netmask from config
# domain_ids = domain_id
# tftp_ids = proxy_id
# dns-primary, dns-secondary, gateway is blank
# get subnet id

# Glabal parameters
# enable-puppetlabs-repo false
# enable-puppetlabs-pc1-repo true
# run-puppet-in-installer true
# time-zone Europe/Oslo
# ntp-server no.pool.ntp.org
# root-pass rootpw_md5
# entries-per-page 100
# foreman-url https://
# unattended-url http://
# trusted-puppetmaster-hosts <foreman-fqdn>
# discovery-fact-column ipmi_ipaddress
# update-ip-from-built-request true
# use-shortname-for-vms true
# idle-timeout 180
#
# check if we can avoid safemode_render bug, and if so
# safemode-render true

# medium
# name CentOS download.iaas.uio.no
# os-family Redhat
# path
# get ids

# sync templates with foreman_templates /api/v2/templates/import
# get provision_id norcams Kickstart default
# get pxelinux_id norcams PXELinux
# get ptable_id norcams ptable default

# associate ptable templates with Redhat

# create and update os
# Create CentOS major 7 minor 6
# associate with family Redhat
# architecture-ids 1
# medium-ids download.iaas.uio.no
# ptable norcams ...
# provision_id + pxelinux_id
# make ^^ default

# create default env production

# create base hostgroup
# name base
# architecture x86_64
# domain $foreman_domain_id
# operatingsystem-id $centos_os
# medium-id $medium_id_2
# partition-table-id $norcams_ptable_id
# subnet-id $foreman_subnet_id
# puppet-proxy-id $foreman_proxy_id
# puppet-ca-proxy-id $foreman_proxy_id
# environment production

# create storage hostgroup
# parent base
# parameter installdevice <config value>

# create compute hosgroup
# parent base
# parameter installdevice <config value>

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
        result = client.create_computeresources(resource)
        found_resources[name] = result['id']
    else:
        logger.debug('=> update compute resource %s' % name)
        result = client.update_computeresources(found_resources[name], resource)

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
            client.destroy_computeprofiles(found_profiles[found_profile])
        else:
            verified_profiles.append(found_profile)

for profile_name in profiles.keys():
    if profile_name not in verified_profiles:
        profile_result = client.create_computeprofiles({'name': profile_name})
        logger.debug("=> create profile result %s" % profile_result)
        for r in found_resources:
            attr_result = client.create_computeattributes(
                compute_profile_id=profile_result['id'],
                compute_resource_id=found_resources[r],
                compute_attribute=profiles[profile_name])
            logger.debug("=> create attributes result %s" % attr_result)
    else:
        ext_profile = client.show_computeprofiles(found_profiles[profile_name])
        for attr in ext_profile['compute_attributes']:
            name = attr['compute_profile_name']
            if attr['vm_attrs'] == profiles[name]['vm_attrs']:
                logger.debug("=> no change for %s" % name)
            else:
                for r in found_resources:
                    result = client.update_computeattributes(
                        compute_profile_id=attr['compute_profile_id'],
                        compute_resource_id=found_resources[r],
                        id=attr['id'],
                        compute_attribute=profiles[name])
                    logger.debug("=> update result %s" % result)
