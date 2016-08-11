#!/usr/bin/env python
""" Update glance images """

import sys
import os
import urllib
import urllib2
import utils
from himlarcli import utils as himutils
from himlarcli.glance import Glance

golden_images = dict()
golden_images['centos'] = {
    'name':             'CentOS 7',
    'url':              'http://cloud.centos.org/centos/7/images/',
    'latest':           'CentOS-7-x86_64-GenericCloud.qcow2',
    'checksum_file':    'sha256sum.txt',
    'checksum':         'sha256',
    'visibility':       'public',
    'disk_format':      'qcow2',
    'min_ram':          768,
    'min_disk':         8
}

golden_images['ubuntu'] = {
    'name':             'Ubuntu server 16.04',
    'url':              'https://cloud-images.ubuntu.com/xenial/current/',
    'latest':           'xenial-server-cloudimg-amd64-disk1.img',
    'checksum_file':    'SHA256SUMS',
    'checksum':         'sha256',
    'visibility':       'public',
    'disk_format':      'qcow2',
    'min_ram':          768,
    'min_disk':         8
}

options = utils.get_options('Create and update golden images', hosts=0)
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
    glclient.create_image(source_path,
                          name=image['name'],
                          visibility=image['visibility'],
                          disk_format=image['disk_format'],
                          min_disk=image['min_disk'],
                          min_ram=image['min_ram'],
                          container_format='bare')

for name, image_data in golden_images.iteritems():
    image = glclient.get_image(image_data['name'])
    if image:
        source_path = download_and_check(image_data)
        md5 = himutils.checksum_file(source_path, 'md5')
        if image['checksum'] != md5:
            glclient.delete_image()
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
    os.remove(source_path)
