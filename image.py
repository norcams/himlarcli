#!/usr/bin/env python

from himlarcli import tests as tests
tests.is_virtual_env()

import os
from datetime import datetime
from himlarcli.keystone import Keystone
from himlarcli.nova import Nova
from himlarcli.glance import Glance
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli import utils as utils

parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)

kc = Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

gc = utils.get_client(Glance, options, logger)

# Distro list
distros = {'fedora': 0, 'centos': 0, 'ubuntu': 0, 'debian': 0, 'cirros': 0, 'windows': 0}

# Mandatory image attributes
mandatory = ['latest', 'url', 'name', 'min_ram', 'min_disk', 'depricated']

def action_grant():
    set_access('grant')

def action_revoke():
    set_access('revoke')

def set_access(image_action):
    project = kc.get_project_by_name(options.project)
    if not project:
        utils.sys_error('Unknown project {}'.format(options.project))
    # Grant based on tags, name or type
    tags = get_tags(names=True)
    tag_str = 'all tags' if not tags else '[' + ', '.join(tags) + ']'
    if not utils.confirm_action('{} access to shared images matching {}'
                                .format(image_action.capitalize(), tag_str)):
        return
    filters = {'status': 'active', 'tag': tags, 'visibility': 'shared'}
    kc.debug_log('filter: {}'.format(filters))
    images = gc.get_images(filters=filters)
    for image in images:
        gc.set_image_access(image_id=image.id, project_id=project.id, action=image_action)
        printer.output_msg('{} access to image {} for project {}'.
                           format(image_action.capitalize(), image.name, options.project))

def action_list_access():
    tags = get_tags(names=True)
    filters = {'status': 'active', 'visibility': 'shared', 'tag': tags}
    kc.debug_log('filter: {}'.format(filters))
    images = gc.get_images(filters=filters)
    for image in images:
        out_image = image.copy()
        out_image['members'] = list()
        members = gc.get_image_access(image.id)
        printer.output_dict({'header': 'Members of {}'.format(image.name)})
        for member in members:
            member_out = {
                'project': kc.get_by_id('project', member.member_id).name,
                'status': member.status
            }
            printer.output_dict(member_out, one_line=True)

def action_list():
    status = 'deactivated' if options.status == 'deactive' else 'active'
    tags = get_tags(names=True)
    filters = {'status': status, 'visibility': options.visibility, 'tag': tags}
    kc.debug_log('filter: {}'.format(filters))
    images = gc.get_images(filters=filters)
    printer.output_dict({'header': 'Image list (id, created_at, tags)'})
    count = 0
    for image in images:
        out_image = {
            '1': image.id,
            '2': image.created_at,
            '3': '[' + ', '.join(image.tags) + ']'
        }
        printer.output_dict(out_image, sort=True, one_line=True)
        count += 1
    out_image = {'header': 'Image count', 'count': count}
    printer.output_dict(out_image)

def action_usage():
    output = get_image_usage(options.detailed)
    out_image = {'header': 'Images with usage count'}
    printer.output_dict(out_image)
    distros['header'] = 'Used distros'
    tag_count = dict()
    tag_count['header'] = 'Used image tags'
    count = 0
    for image in output.itervalues():
        count += 1
        out_image = {
            'name': image['name'],
            'id': image['id'],
            'count': image['count']}
        if options.detailed:
            out_image['instances'] = image['instances']
            out_image['created_at'] = image['created_at']
            out_image['tags'] = image['tags']
        one_line = False if options.detailed else True
        printer.output_dict(out_image, sort=True, one_line=one_line)
        for distro in distros.iterkeys():
            if distro in image['name'].lower():
                for tag in image['tags']:
                    tag_count[tag] = tag_count.get(tag, 0) + image['count']
                distros[distro] += image['count']
                continue
    printer.output_dict(distros)
    printer.output_dict(tag_count)
    printer.output_dict({'header': 'Image count', 'count': count})
    return output

def action_purge():
    tags = get_tags(names=True)
    tag_str = 'all tags' if not tags else '[' + ', '.join(tags) + ']'
    if not utils.confirm_action('Purge unused {} deactive images matching {}'
                                .format(options.visibility, tag_str)):
        return
    images = get_image_usage()
    count = 0
    printer.output_dict({'header': 'Images deleted'})
    limit = int(options.limit) if options.limit else options.limit
    for image in images.itervalues():
        if image['count'] > 0:
            kc.debug_log('no purge: image {} in use!'.format(image['name']))
            continue
        gc.delete_image(image['id'])
        out_image = {
            '1': image.name,
            '2': image.created_at,
            '3': '[' + ', '.join(image.tags) + ']'
        }
        printer.output_dict(out_image, sort=True, one_line=True)
        count += 1
        # break purging if limit reached
        if limit and count >= int(limit):
            kc.debug_log('limit of {} reached'.format(limit))
            break
    printer.output_dict({'header': 'Image count', 'count': count})

def action_retire():
    tags = get_tags(names=True)
    tag_str = 'all tags' if not tags else '[' + ', '.join(tags) + ']'

    # Load config file
    config_filename = 'config/images/{}'.format(options.image_config)
    if not utils.file_exists(config_filename, logger):
        utils.sys_error('Could not find config file {}'.format(config_filename))
    image_config = utils.load_config('config/images/{}'.format(options.image_config))
    if 'images' not in image_config or 'type' not in image_config:
        utils.sys_error('Images hash not found in config file {}'.format(config_filename))

    if options.name not in image_config['images']:
        utils.sys_error('Unable to retire {}. Missing from config file {}'
                        .format(options.name, options.image_config))

    # Point of no return
    if not utils.confirm_action('Retire active images matching {}'
                                .format(tag_str)):
        return

    # Find image(s)
    tags = get_tags(names=True)
    filters = {'status': 'active', 'tag': tags}
    kc.debug_log('filter: {}'.format(filters))
    images = gc.get_images(filters=filters, limit=1)
    for image in images:
        new_name = image_config['images'][options.name]['depricated']
        timestamp = datetime.utcnow().replace(microsecond=0).isoformat()
        gc.update_image(image_id=image['id'],
                        name=new_name,
                        depricated=timestamp)
        gc.deactivate(image_id=image['id'])
        printer.output_msg('Retire image {}'.format(image['name']))

def action_update():
    # Load config file
    config_filename = 'config/images/{}'.format(options.image_config)
    if not utils.file_exists(config_filename, logger):
        utils.sys_error('Could not find config file {}'.format(config_filename))
    image_config = utils.load_config('config/images/{}'.format(options.image_config))
    if 'images' not in image_config or 'type' not in image_config:
        utils.sys_error('Images hash not found in config file {}'.format(config_filename))

    image_type = image_config['type']
    for name, image_data in image_config['images'].iteritems():
        if 'retired' in image_data and image_data['retired'] == 1:
            kc.debug_log('dropped {}: image retired'.format(name))
            continue
        if options.name and name != options.name:
            kc.debug_log('dropped {}: image name spesified'.format(name))
            continue
        if not bool(all(k in image_data for k in mandatory)):
            kc.debug_log('missing attributes in image hash for {}'.format(name))
            continue
        update_image(name, image_data, image_type)

def get_image_usage(detailed=False):
    if hasattr(options, 'status'):
        status = 'deactivated' if options.status == 'deactive' else 'active'
    else:
        status = 'deactivated'
    nc = utils.get_client(Nova, options, logger)
    tags = get_tags(names=True)
    filters = {'status': status, 'visibility': options.visibility, 'tag': tags}
    kc.debug_log('filter: {}'.format(filters))
    image_usage = dict()
    images = gc.get_images(limit=1000, page_size=999, filters=filters)
    for image in images:
        image_usage[image.id] = image
        image_usage[image.id]['count'] = 0
        search_opts = {'image': image.id}
        instances = nc.get_all_instances(search_opts=search_opts)
        if detailed:
            image_usage[image.id]['instances'] = list()
        for i in instances:
            image_usage[image.id]['count'] += 1
            if detailed:
                image_usage[image.id]['instances'].append(i.id)
    return image_usage

def update_image(name, image_data, image_type):
    if 'checksum' in image_data and 'checksum_file' in image_data:
        checksum_url = "%s%s" % (image_data['url'], image_data['checksum_file'])
        checksum_type = image_data['checksum']
    else:
        checksum_type = checksum_url = None
    url = (image_data['url'] + image_data['latest'])
    imagefile = utils.download_file(image_data['latest'], url, logger,
                                    checksum_type, checksum_url, 10000)
    if not imagefile: # if download or checksum failed
        kc.debug_log('download {} failed'.format(url))
        return
    # set tags
    tags = list()
    tags.append(image_type)
    tags.append(name)
    # Filter based on tags: type and name (only one of each type should exists)
    filters = {'tag': tags, 'status': 'active'}
    kc.debug_log('filter: {}'.format(filters))
    images = gc.find_image(filters=filters, limit=1)
    if images and len(images) == 1:
        kc.debug_log('image {} found'.format(name))
        checksum = utils.checksum_file(imagefile, 'md5')
        if checksum != images[0]['checksum']:
            kc.debug_log('update image: new checksum found {}'.format(checksum))
            result = create_image(name, imagefile, image_data, image_type)
            timestamp = datetime.utcnow().replace(microsecond=0).isoformat()
            gc.update_image(image_id=images[0]['id'],
                            name=image_data['depricated'],
                            depricated=timestamp)
            gc.deactivate(image_id=images[0]['id'])
            # keep access to shared images
            if images[0]['visibility'] == 'shared':
                members = gc.get_image_access(images[0]['id'])
                for member in members:
                    if not options.dry_run:
                        gc.set_image_access(project_id=member.member_id,
                                            image_id=result.id, action='grant')
                    else:
                        gc.debug_log('grant access to new image for {}'
                                     .format(member.member_id))
        else:
            result = None
            kc.debug_log('no new image needed: checksum match found')
    else:
        kc.debug_log('image {} not found'.format(name))
        result = create_image(name, imagefile, image_data, image_type)
    if result:
        kc.debug_log(result)

    # Cleanup
    if not options.skip_cleanup and os.path.isfile(imagefile):
        os.remove(imagefile)

def create_image(name, source_path, image, image_type):
    # Populate input with default values if not defined in config
    visibility = image['visibility'] if 'visibility' in image else 'private'
    disk_format = image['disk_format'] if 'disk_format' in image else 'qcow2'
    container_format = image['container_format'] if 'container_format' in image else 'bare'
    # Properties hash from yaml
    properties = {}
    if 'properties' in image:
        for key, value in image['properties'].iteritems():
            properties[key] = value
    # Create tags and tag all images with type and name
    tags = list()
    tags.append(image_type)
    tags.append(name)
    if 'tags' in image:
        for tag in image['tags']:
            tags.append(tag)
    # Set image owner
    if 'owner' in image:
        project = kc.get_project_by_name(image['owner'])
        if not project:
            utils.sys_error('project {} not found!'.format(image['owner']), 0)
            image_owner = None
        else:
            image_owner = project.id
    else:
        image_owner = None # no owner is set

    result = gc.create_image(source_path,
                             name=image['name'],
                             visibility=visibility,
                             disk_format=disk_format,
                             min_disk=image['min_disk'],
                             min_ram=image['min_ram'],
                             container_format=container_format,
                             tags=tags,
                             owner=image_owner,
                             **properties)
    return result

def get_tags(names=False):
    tags = list()
    if hasattr(options, 'type'):
        if options.type != 'all':
            tags.append(options.type)
    if names and options.name:
        tags.append(options.name)
    return tags

# Run local function with the same name as the action (Note: - => _)
action = locals().get('action_' + options.action.replace('-', '_'))
if not action:
    utils.sys_error("Function action_%s() not implemented" % options.action)
action()
