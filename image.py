#!/usr/bin/env python

""" Manage images """

import sys
import os
from datetime import datetime
from himlarcli import utils as himutils
from himlarcli.glance import Glance
from himlarcli.nova import Nova
from himlarcli.parser import Parser
from himlarcli.printer import Printer

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)
glclient = Glance(options.config, debug=options.debug, region=options.region)
logger = glclient.get_logger()

# Filters
tags = list()
if options.type != 'all':
    tags.append(options.type)

def action_purge():
    if not himutils.confirm_action('Purge unused images'):
        return
    images = image_usage()
    for image in images.itervalues():
        if image['count'] > 0:
            logger.debug('=> no purge: image %s in use!' % image['name'])
            continue
        log_msg = "delete image %s" % image['name']
        if not options.dry_run:
            glclient.delete_image(image['id'])
        else:
            log_msg = "DRY-RUN: %s" % log_msg
        logger.debug('=> %s', log_msg)

def action_usage():
    output = image_usage()
    out_image = {'header': 'Image usage (count, id, name)'}
    printer.output_dict(out_image)
    distros = {'fedora': 0, 'centos': 0, 'ubuntu': 0, 'debian': 0, 'cirros': 0}
    distros['header'] = 'Distros'
    for image in output.itervalues():
        out_image = {
            'name': image['name'],
            'id': image['id'],
            'count': image['count']}
        printer.output_dict(out_image, sort=False, one_line=True)
        for distro in distros.iterkeys():
            if distro in image['name'].lower():
                distros[distro] += image['count']
                continue
    printer.output_dict(distros)
    return output

def action_list():
    status = 'deactivated' if options.deactive else 'active'
    filters = {'status': status, 'visibility': options.visibility, 'tag': tags}
    logger.debug('=> filter: %s' % filters)
    images = glclient.get_images(filters=filters)
    out_image = {'header': 'Image list (id, name, created_at)'}
    printer.output_dict(out_image)
    for image in images:
        out_image = {'name': image.name, 'created': image.created_at, 'id': image.id}
        printer.output_dict(out_image, sort=False, one_line=True)

def action_update():
    image_templates = himutils.load_config('config/images/%s' % options.image_config)
    if not image_templates or 'images' not in image_templates:
        sys.stderr.write("Invalid yaml file (config/images/%s): images hash not found\n"
                         % options.image_config)
        sys.exit(1)
    for name, image_data in image_templates['images'].iteritems():
        if options.name and name != options.name:
            logger.debug('=> dropped %s: image name spesified', name)
            continue
        mandatory = ['latest', 'url', 'name', 'min_ram', 'min_disk', 'depricated']
        if not bool(all(k in image_data for k in mandatory)):
            logger.debug('=> missing attributes in image hash for %s' % name)
            continue
        update_image(name, image_data)

def image_usage():
    status = 'deactivated' if options.deactive else 'active'
    novaclient = Nova(options.config, debug=options.debug, log=logger, region=options.region)
    filters = {'status': status, 'visibility': options.visibility, 'tag': tags}
    logger.debug('=> filter: %s' % filters)
    image_usage = dict()
    images = glclient.get_images(limit=1000, page_size=999, filters=filters)
    for image in images:
        image_usage[image.id] = image
        image_usage[image.id]['count'] = 0
        search_opts = {'image': image.id}
        instances = novaclient.get_all_instances(search_opts=search_opts)
        for i in instances:
            image_usage[i.image['id']]['count'] += 1
    return image_usage

def update_image(name, image_data):
    if 'checksum' in image_data and 'checksum_file' in image_data:
        checksum_url = "%s%s" % (image_data['url'], image_data['checksum_file'])
        checksum_type = image_data['checksum']
    else:
        checksum_type = checksum_url = None
    url = (image_data['url'] + image_data['latest'])
    imagefile = himutils.download_file(image_data['latest'], url, logger,
                                       checksum_type, checksum_url)
    if not imagefile: # if download or checksum failed
        return
    tags = list(image_data['tags']) if 'tags' in image_data else list()
    tags.append(options.type)
    filters = {'name': image_data['name'], 'tag': tags}
    images = glclient.find_image(filters=filters, limit=1)
    if images and len(images) == 1:
        logger.debug('=> image %s found' % name)
        checksum = himutils.checksum_file(imagefile, 'md5')
        if checksum != images[0]['checksum']:
            logger.debug('=> update image: new checksum found %s' % checksum)
            result = create_image(name, imagefile, image_data)
            if not options.dry_run:
                timestamp = datetime.utcnow().isoformat()
                glclient.update_image(image_id=images[0]['id'],
                                      name=image_data['depricated'],
                                      depricated=timestamp)
                glclient.deactivate(image_id=images[0]['id'])
        else:
            result = None
            logger.debug('=> no new image needed: checksum match found')
    else:
        logger.debug('=> image %s not found' % name)
        result = create_image(name, imagefile, image_data)
    if result:
        logger.debug('=> %s' % result)

    # Cleanup
    if os.path.isfile(imagefile):
        os.remove(imagefile)

def create_image(name, source_path, image):
    # Populate input with default values if not defined in config
    visibility = image['visibility'] if 'visibility' in image else 'private'
    disk_format = image['disk_format'] if 'disk_format' in image else 'qcow2'
    container_format = image['container_format'] if 'container_format' in image else 'bare'
    # Properties hash from yaml
    properties = {}
    if 'properties' in image:
        for key, value in image['properties'].iteritems():
            properties[key] = value
    tags = list()
    # Tag all images with type and name
    tags.append(options.type)
    tags.append(name)
    if 'tags' in image:
        for tag in image['tags']:
            tags.append(tag)
    log_msg = "create new image %s" % image['name']
    if not options.dry_run:
        result = glclient.create_image(source_path,
                                       name=image['name'],
                                       visibility=visibility,
                                       disk_format=disk_format,
                                       min_disk=image['min_disk'],
                                       min_ram=image['min_ram'],
                                       container_format=container_format,
                                       tags=tags,
                                       **properties)
    else:
        log_msg = 'DRY-RUN: ' + log_msg
        result = None
    logger.debug('=> %s' % log_msg)
    return result

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
