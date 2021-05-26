import sys
import os
from datetime import datetime
from datetime import date
import ConfigParser
import logging
import logging.config
import inspect
#import warnings
import yaml
import hashlib
import functools
#import mimetypes
import urllib
import urllib2
from string import Template
import socket
from tabulate import tabulate

def get_client(name, options, logger, region=None):
    if region:
        client = name(options.config, debug=options.debug,
                      region=region, log=logger)
    else:
        client = name(options.config, debug=options.debug, log=logger)
    client.set_dry_run(options.dry_run)
    return client

def get_regions(options, keystoneclient):
    # Region
    if hasattr(options, 'region'):
        regions = keystoneclient.find_regions(region_name=options.region)
    else:
        regions = keystoneclient.find_regions()
    keystoneclient.debug_log('regions used {}'.format(','.join(regions)))
    return regions

def sys_error(text, code=1):
    sys.stderr.write("%s\n" % text)
    if code > 0:
        sys.exit(code)

def check_port(address, port, timeout=60, log=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((address, int(port)))
        if log:
            log.debug("=> Connected to %s on port %s" % (address, port))
        sock.close()
        return True
    except socket.error, e:
        if log:
            log.debug("=> Connection to %s on port %s failed: %s" % (address, port, e))
        return False

def confirm_action(question):
    question = "%s (yes|no)? " % question
    answer = raw_input(question)
    if answer.lower() == 'yes':
        return True
    sys.stderr.write('Action aborted by user.\n')
    return False

def append_to_file(filename, text):
    filename = get_abs_path(filename)
    f = open(filename, 'a+')
    f.write("%s\n" % text)
    f.close()

def append_to_logfile(filename, date, region, text1, text2, text3):
    filename = get_abs_path(filename)
    try:
        f = open(filename, 'a+')
        try:
            f.write("%s, %s, %s, %s, %s\n" % (date, region, text1, text2, text3))
	finally:
            f.close()
    except IOError as exc:
        logger.warn('=> ERROR: could not append to logfile %s' % exc)

def get_config(config_path):
    if not os.path.isfile(config_path):
        logging.critical("Could not find config file: %s", config_path)
        sys.exit(1)
    config = ConfigParser.ConfigParser()
    config.read(config_path)
    return config

def get_current_date(format='%Y-%m-%dT%H:%M:%S.%f%z'):
    current_date = datetime.now()
    return current_date.strftime(format)

def get_date(datestr, default, format='%d.%m.%Y'):
    if datestr:
        try:
            return datetime.strptime(datestr, format).date()
        except ValueError:
            sys_error('date format %s not valid for %s' % (format, datestr), 1)
    else:
        return default

def past_date(datestr, format='%Y-%m-%d'):
    if datestr:
        try:
            past = datetime.strptime(datestr, format).date()
            today = date.today()
            if past < today:
                return True
        except ValueError as e:
            sys_error(e, 0)
    return False

def convert_date(datestr, old_format, new_format='%Y-%m-%d'):
    return datetime.strptime(datestr, old_format).strftime(new_format)

def get_logger(name, config, debug, log=None):
    if log:
        mylog = log
    else:
        try:
            path = config.get('log', 'path')
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            path = '/opt/himlarcli/'
        mylog = setup_logger(name, debug, path)
        if not os.environ.get('VIRTUAL_ENV'):
            caller = inspect.stack()[1][1].replace('/opt/himlarcli', '')
        else:
            caller = inspect.stack()[1][1].replace(os.environ.get('VIRTUAL_ENV'), '')
        mylog.debug('=> logger startet from %s at %s', caller, datetime.now())
        mylog.debug('=> logger config loaded from logging.yaml')
    return mylog

def is_virtual_env():
    if not hasattr(sys, 'real_prefix'):
        print "Remember to source bin/activate!"
        sys.exit(1)

def setup_logger(name, debug, log_path='/opt/himlarcli/', configfile='logging.yaml'):
    if not os.path.isfile(configfile):
        configfile = log_path + '/' + configfile
    with open(configfile, 'r') as stream:
        try:
            config = yaml.full_load(stream)
        except yaml.YAMLError as exc:
            print exc

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

def file_exists(test_file, log=None):
    test_file = get_abs_path(test_file)
    if not os.path.isfile(test_file):
        if log:
            log.debug('=> file not found: %s' % test_file)
        return False
    return True

def load_config(configfile, log=None):
    configfile = get_abs_path(configfile)
    if not os.path.isfile(configfile):
        if log:
            log.debug('=> config file not found: %s' % configfile)
        return None
    with open(configfile, 'r') as stream:
        try:
            config = yaml.full_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            config = None
    return config

def get_instance_table(instances, columns=None, tablefmt='simple'):
    if not columns:
        columns = ['status', 'region']
    tables = list()
    for i in instances:
        instance = [i['name']]
        for k, v in i.iteritems():
            if k in columns:
                instance.append(v)
        tables.append(instance)

    header = ['NAME']
    for k in next(iter(instances)):
        if k in columns:
            header.append(k.upper())
    return tabulate(tables, headers=header, tablefmt=tablefmt)

def download_file(target, source, logger, checksum_type=None, checksum_url=None, content_length=1000):
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
        if int(headers['content-length']) < content_length:
            logger.debug("=> file is too small: %s" % target)
            if os.path.isfile(target):
                os.remove(target)
            return None
    if checksum_type and checksum_url:
        checksum = checksum_file(target, checksum_type)
        try:
            response = urllib2.urlopen(checksum_url)
        except urllib2.HTTPError as exc:
            logger.debug('=> {}'.format(exc))
            logger.debug('=> unable to download checksum {}'.format(checksum_url))
            return None
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
