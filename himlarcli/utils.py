import sys
import os
import ConfigParser
import logging
import netifaces
import ipaddress
import logging
import logging.config
import warnings
import yaml
import hashlib
import functools

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
        mylog = setup_logger(name, debug)
    return mylog

def has_network_access(network, log=None):
    net = ipaddress.ip_network(network)
    if log:
        log.debug("Testing access to %s" % net)
        log.debug("Interfaces: " + ", ".join(netifaces.interfaces()))
    inf = netifaces.interfaces()
    for i in inf:
        addrs = netifaces.ifaddresses(i)
        try:
            for addr in addrs[netifaces.AF_INET]:
                ip_addr = ipaddress.ip_address(addr['addr'])
                if ip_addr.is_loopback:
                    continue
                if ip_addr in net:
                    if log:
                        log.debug("Interface %s has access to %s" % (i, net))
                    return True
        except KeyError as e:
            pass
    return False

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

def load_config(configfile):
    configfile = get_abs_path(configfile)
    with open(configfile, 'r') as stream:
        try:
            config = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            config = None
    return config

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
