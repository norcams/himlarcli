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

print "Depricated! Use image.py"
print "This will only set images to outdated"

options = utils.get_options('Create and update golden images',
                             hosts=0, dry_run=True)
glclient = Glance(options.config, debug=options.debug)
logger = glclient.get_logger()
golden_images = himutils.load_config('config/golden_images.yaml')
if glclient.region in golden_images:
    images = golden_images[glclient.region]
else:
    if not 'default' in golden_images:
        print "Missing default in config/golden_images.yaml"
        sys.exit(1)
    images = golden_images['default']

def download_and_check(image):
    source = himutils.get_abs_path('%s' % image['latest'])
    url = '%s%s' % (image['url'], image['latest'])
    # Do not redownload
    if not os.path.isfile(source):
        (filename, headers) = urllib.urlretrieve(url, source)
        if int(headers['content-length']) < 1000:
            logger.debug("=> file is too small: %s" % url)
            os.remove(source)
            return None
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
        region = glclient.get_config('openstack', 'region')
        res = glclient.create_image(source_path,
                                    name=image['name'],
                                    visibility=image['visibility'],
                                    disk_format=image['disk_format'],
                                    min_disk=image['min_disk'],
                                    min_ram=image['min_ram'],
                                    container_format='bare',
                                    region=region)
        print "New image created:"
        pp = pprint.PrettyPrinter(indent=1)
        pp.pprint(res)

for name, image_data in images.iteritems():
    region = glclient.get_config('openstack', 'region')
    image = glclient.get_image(image_data['name'])
    if image and (image['region'] == region):
        source_path = download_and_check(image_data)
        if not source_path:
            continue
        md5 = himutils.checksum_file(source_path, 'md5')
        if image['checksum'] != md5:
            timestamp = datetime.utcnow().isoformat()
            if not options.dry_run:
                glclient.update_image(name=image_data['depricated'],
                                      depricated=timestamp)
                glclient.deactivate()
            logger.debug("=> depricated old image for %s" % image['name'])
            #create_image(glclient, source_path, image_data)
        else:
            logger.debug("=> no new image for %s" % image['name'])
    else:
        source_path = download_and_check(image_data)
        if source_path:
            pass
            #create_image(glclient, source_path, image_data)
        else:
            logger.error("=> checksum failed for %s" % name)
    # Clean up
    if source_path:
        os.remove(source_path)
    else:
        logger.error("=> image download failed %s" % name)
