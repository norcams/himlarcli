#!/usr/bin/env python
""" Update glance images """

import sys
import os
import urllib
import urllib2
import pprint
from datetime import datetime
import utils
from himlarcli import utils as himutils
from himlarcli.glance import Glance

# Import golden images from misc
misc_path = himutils.get_abs_path('misc')
sys.path.append(misc_path)
import golden_images

options = utils.get_options('Create and update golden images',
                             hosts=0, dry_run=True)
glclient = Glance(options.config, debug=options.debug)
logger = glclient.get_logger()

def download_and_check(image):
    source = himutils.get_abs_path('%s' % image['latest'])
    url = '%s%s' % (image['url'], image['latest'])
    # Do not redownload
    if not os.path.isfile(source):
        urllib.urlretrieve(url, source)
    checksum = himutils.checksum_file(source, image['checksum'])
    checksum_url = "%s%s" % (image['url'], image['checksum_file'])
    response = urllib2.urlopen(checksum_url)
    checksum_all = response.read()
    if checksum in checksum_all:
        logger.debug("=> checksum ok: %s" % checksum)
        return source
    else:
        return None

def create_image(glclient, source_path, image):
    if not options.dry_run:
        res = glclient.create_image(source_path,
                                    name=image['name'],
                                    visibility=image['visibility'],
                                    disk_format=image['disk_format'],
                                    min_disk=image['min_disk'],
                                    min_ram=image['min_ram'],
                                    container_format='bare')
        print "New image created:"
        pp = pprint.PrettyPrinter(indent=1)
        pp.pprint(res)

for name, image_data in golden_images.images.iteritems():
    image = glclient.get_image(image_data['name'])
    if image:
        source_path = download_and_check(image_data)
        md5 = himutils.checksum_file(source_path, 'md5')
        if image['checksum'] != md5:
            timestamp = datetime.utcnow().isoformat()
            if not options.dry_run:
                glclient.update_image(name=image_data['depricated'],
                                      visibility='private',
                                      depricated=timestamp)
            logger.debug("=> depricated old image for %s" % image['name'])
            create_image(glclient, source_path, image_data)
        else:
            logger.debug("=> no new image for %s" % image['name'])
    else:
        source_path = download_and_check(image_data)
        if source_path:
            create_image(glclient, source_path, image_data)
        else:
            logger.error("=> checksum failed for %s" % name)
    # Clean up
    if source_path:
        os.remove(source_path)
    else:
        logger.error("=> image download failed %s" % name)
