#!/usr/bin/env python

""" Manage images """

import sys
import os
from himlarcli import utils as himutils
from himlarcli.glance import Glance
from himlarcli.parser import Parser
from himlarcli.printer import Printer

himutils.is_virtual_env()

# Load parser config from config/parser/*
parser = Parser()
options = parser.parse_args()
printer = Printer(options.format)
glclient = Glance(options.config, debug=options.debug, region=options.region)
logger = glclient.get_logger()

def action_list():
    filters = {'status': 'active', 'visibility': 'public'}
    images = glclient.get_images(filters=filters)
    output = output = dict({'images': list()})
    output['header'] = 'Public active images:'
    for image in images:
        out_image = {'name': image.name, 'created': image.created_at}
#        out_image['header'] = image.name
        printer.output_dict(out_image, sort=False)
        output['images'].append(image.name)

def action_update():
    image_templates = himutils.load_config('config/images/%s' % options.image_config)
    if not image_templates or 'images' not in image_templates:
        sys.stderr.write("Invalid yaml file (config/images/%s): images hash not found\n"
                         % options.image_config)
        sys.exit(1)
    for name, image_data in image_templates['images'].iteritems():
        mandatory = ['latest', 'url']
        if not bool(all(k in image_data for k in mandatory)):
            logger.debug('=> missing attributes in image hash for %s' % name)
            continue
        url = (image_data['url'] + image_data['latest'])
        imagefile = himutils.download_file(image_data['latest'], url, logger)
        print imagefile
        #TODO: add tag list
        filters = {'name': image_data['name']}
        images = glclient.find_image(filters=filters, limit=1)
        if images:
            logger.debug('=> image %s found' % name)
        else:
            logger.debug('=> image %s not found' % name)
        #for image in images:
        #    print image
        # Cleanup
        if os.path.isfile(imagefile):
            os.remove(imagefile)

# Run local function with the same name as the action
action = locals().get('action_' + options.action)
if not action:
    logger.error("Function action_%s not implemented" % options.action)
    sys.exit(1)
action()
