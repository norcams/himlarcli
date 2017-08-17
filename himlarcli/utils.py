import sys
import os
import ConfigParser
import logging
import logging.config
#import warnings
import yaml
import hashlib
import functools
#import mimetypes
import urllib
import urllib2
from string import Template


def sys_error(text, code=1):
    sys.stderr.write("%s\n" % text)
    sys.exit(code)

def confirm_action(question):
    question = "%s (yes|no)? " % question
    answer = raw_input(question)
    if answer.lower() == 'yes':
        return True
    sys.stderr.write('Action aborted by user.\n')
    return False

def get_config(config_path):
    if not os.path.isfile(config_path):
        logging.critical("Could not find config file: %s" %config_path)
        sys.exit(1)
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    return config

def get_logger(name, config, debug, log=None):
    if log:
        mylog = log
    else:
        try:
            path = config.get('log', 'path')
        except ConfigParser.NoOptionError:
            path = '/opt/himlarcli/'
        mylog = setup_logger(name, debug, path)
    return mylog

def is_virtual_env():
    if not hasattr(sys, 'real_prefix'):
        print "Remember to source bin/activate!"
        sys.exit(1)

def setup_logger(name, debug,
                 log_path = '/opt/himlarcli/',
                 configfile = 'logging.yaml'):
    if not os.path.isabs(configfile):
        configfile = log_path + '/' + configfile
    with open(configfile, 'r') as stream:
        try:
            config = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Always use absolute paths
    if not os.path.isabs(config['handlers']['file']['filename']):
        config['handlers']['file']['filename'] = log_path + \
            config['handlers']['file']['filename']
    if config:
        try:
            logging.config.dictConfig(config)
        except ValueError as e:
            print e
            print "Please check your log section in config.ini and logging.yaml"
            sys.exit(1)
    logger = logging.getLogger(name)
    logging.captureWarnings(True)
    # If debug add verbose console logger
    if (debug):
        ch = logging.StreamHandler()
        format = '%(message)s [%(module)s.%(funcName)s():%(lineno)d]'
        formatter = logging.Formatter(format)
        ch.setFormatter(formatter)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        #print "%s: loglevel %s" % (name, logging.DEBUG)
    return logger

def get_abs_path(file):
    abs_path = file
    if not os.path.isabs(file):
        install_dir = os.environ.get('VIRTUAL_ENV')
        if not install_dir:
            install_dir = '/opt/himlarcli'
        abs_path = install_dir + '/' + file
    return abs_path

def load_template(inputfile, mapping, log=None):
    inputfile = get_abs_path(inputfile)
    if not os.path.isfile(inputfile):
        if log:
            log.debug('=> file not found: %s' % inputfile)
        return None
    with open(inputfile, 'r') as txt:
        content = txt.read()
    template = Template(content)
    return template.substitute(mapping)

def load_txt_file(inputfile, log=None):
    inputfile = get_abs_path(inputfile)
    if not os.path.isfile(inputfile):
        if log:
            log.debug('=> file not found: %s' % inputfile)
        return None
    with open(inputfile, 'r') as txt:
        content = txt.read()
    return content

def load_file(inputfile, log=None):
    inputfile = get_abs_path(inputfile)
    if not os.path.isfile(inputfile):
        if log:
            log.debug('=> file not found: %s' % inputfile)
        return {}
    with open(inputfile, 'r') as stream:
        data = stream.read().splitlines()
    return data

def load_region_config(configpath, filename='default', region=None, log=None):
    regionfile = get_abs_path('%s/%s.yaml' % (configpath, region))
    if os.path.isfile(regionfile):
        configfile = '%s/%s.yaml' % (configpath, region)
    else:
        configfile = '%s/%s.yaml' % (configpath, filename)
    return load_config(configfile, log)

def load_config(configfile, log=None):
    configfile = get_abs_path(configfile)
    if not os.path.isfile(configfile):
        if log:
            log.debug('=> config file not found: %s' % configfile)
        return None
    with open(configfile, 'r') as stream:
        try:
            config = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            config = None
    return config

def download_file(target, source, logger, checksum_type=None, checksum_url=None):
    """ Download a file from a source url """
    target = get_abs_path(target)
    if not os.path.isfile(target):
        try:
            (filename, headers) = urllib.urlretrieve(source, target)
        except IOError as exc:
            logger.warn('=> ERROR: could not download %s' % source)
            sys.stderr.write(str(exc)+'\n')
            return None
        #print filename
        if int(headers['content-length']) < 1000:
            logger.debug("=> file is too small: %s" % target)
            if os.path.isfile(target):
                os.remove(target)
            return None
    if checksum_type and checksum_url:
        checksum = checksum_file(target, checksum_type)
        response = urllib2.urlopen(checksum_url)
        checksum_all = response.read()
        if checksum not in checksum_all:
            logger.debug("=> checksum failed: %s" % checksum)
            return None
        else:
            logger.debug("=> checksum ok: %s" % checksum)
    return target

def checksum_file(file_path, type='sha256', chunk_size=65336):
    # Read the file in small pieces, so as to prevent failures to read particularly large files.
    # Also ensures memory usage is kept to a minimum. Testing shows default is a pretty good size.
    assert isinstance(chunk_size, int) and chunk_size > 0
    if type == 'sha256':
        digest = hashlib.sha256()
    elif type == 'md5':
        digest = hashlib.md5()
    with open(file_path, 'rb') as f:
        [digest.update(chunk) for chunk in iter(functools.partial(f.read, chunk_size), '')]
    return digest.hexdigest()
