import sys
import os
from datetime import datetime
from datetime import date
import configparser
import logging
import logging.config
import inspect
#import warnings
import yaml
import hashlib
import functools
#import mimetypes
import urllib.request
import urllib.error
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

def improved_sys_error(text, msg_type='info', exit_code=0):
    """
    This function prints a message with the designated message type or
    severity level: info, warning, error or fatal. In the case of a
    fatal message, the function also calls exit() with the given exit
    code. Takes 3 parameters:

    text      : The message to be shown
    msg_type  : Message type, on of info / warning / error / fatal
    exit_code : In case of fatal severity, the code for which to call
                exit()

    Author: trondham@uio.no
    Date: 2023-02-16
    """
    #------------------------------+-----------------------------------+---------+
    #       Text color             |       Background color            |         |
    #--------------+---------------+----------------+------------------+         |
    # Base color   |Lighter shade  |  Base color    | Lighter shade    |         |
    #--------------+---------------+----------------+------------------+         |
    BLK='\033[30m'; blk='\033[90m'; BBLK='\033[40m'; bblk='\033[100m' #| Black   |
    RED='\033[31m'; red='\033[91m'; BRED='\033[41m'; bred='\033[101m' #| Red     |
    GRN='\033[32m'; grn='\033[92m'; BGRN='\033[42m'; bgrn='\033[102m' #| Green   |
    YLW='\033[33m'; ylw='\033[93m'; BYLW='\033[43m'; bylw='\033[103m' #| Yellow  |
    BLU='\033[34m'; blu='\033[94m'; BBLU='\033[44m'; bblu='\033[104m' #| Blue    |
    MGN='\033[35m'; mgn='\033[95m'; BMGN='\033[45m'; bmgn='\033[105m' #| Magenta |
    CYN='\033[36m'; cyn='\033[96m'; BCYN='\033[46m'; bcyn='\033[106m' #| Cyan    |
    WHT='\033[37m'; wht='\033[97m'; BWHT='\033[47m'; bwht='\033[107m' #| White   |
    #------------------------------------------------------------------+---------+
    # Effects                                                                    |
    #----------------------------------------------------------------------------+
    DEF='\033[0m'   #Default color and effects                                   |
    BLD='\033[1m'   #Bold\brighter                                               |
    DIM='\033[2m'   #Dim\darker                                                  |
    CUR='\033[3m'   #Italic font                                                 |
    UND='\033[4m'   #Underline                                                   |
    INV='\033[7m'   #Inverted                                                    |
    COF='\033[?25l' #Cursor Off                                                  |
    CON='\033[?25h' #Cursor On                                                   |
    #----------------------------------------------------------------------------+

    # Set colors based on message type
    if msg_type == 'warning':
        prefix = 'WARNING'
        color  = YLW
    elif msg_type == 'error':
        prefix = 'ERROR'
        color  = RED
    elif msg_type == 'fatal':
        prefix = 'FATAL ERROR'
        color  = '%s%s' % (RED,BLD)
    else:
        prefix = 'INFO'
        color  = GRN

    # Only set color if we have a TTY
    if sys.stdout.isatty():
        COLOR_START = color
        COLOR_END   = DEF
    else:
        COLOR_START = ''
        COLOR_END   = ''

    # Print out the message
    if msg_type == 'info' or msg_type == 'warning':
        sys.stdout.write("[%s%s%s] %s\n" % (COLOR_START,prefix,COLOR_END,text))
    elif msg_type == 'fatal':
        sys.stderr.write("%s%s: %s%s\n" % (COLOR_START,prefix,text,COLOR_END))
    else:
        sys.stderr.write("[%s%s%s] %s\n" % (COLOR_START,prefix,COLOR_END,text))
        
    # If message type is "fatal", exit with the given exit_code
    if msg_type == 'fatal':
        sys.exit(exit_code)

def info(text):
    """ Prints an info level message """
    improved_sys_error(text,'info')

def warning(text):
    """ Prints a warning level message """
    improved_sys_error(text,'warning')

def error(text):
    """ Prints an error level message """
    improved_sys_error(text,'error')

def fatal(text, exit_code=1):
    """ Prints a fatal level message and calls exit() with exit_code """
    improved_sys_error(text,'fatal',exit_code)

def check_port(address, port, timeout=60, log=None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((address, int(port)))
        if log:
            log.debug("=> Connected to %s on port %s" % (address, port))
        sock.close()
        return True
    except(socket.error, e):
        if log:
            log.debug("=> Connection to %s on port %s failed: %s" % (address, port, e))
        return False

def confirm_action(question):
    question = "%s (yes|no)? " % question
    answer = input(question)
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
        with open(filename) as f:
            f.write("%s, %s, %s, %s, %s\n" % (date, region, text1, text2, text3))
            f.close()
    except IOError as exc:
        logger.warn('=> ERROR: could not append to logfile %s' % exc)

def get_himlarcli_config(config_path):
    if config_path and not os.path.isfile(config_path):
        Client.log_error("Could not find config file: {}".format(config_path), 1)
    elif not config_path:
        local_config = get_abs_path('config.ini')
        etc_config = '/etc/himlarcli/config.ini'
        if os.path.isfile(local_config):
            found_config_path = local_config
        else:
            if os.path.isfile(etc_config):
                found_config_path = etc_config
        if not found_config_path:
            msg = "Config file not found in default locations:\n  {}\n  {}"
            Client.log_error(msg.format(local_config, etc_config), 1)
    else:
        found_config_path = config_path
    return get_config(found_config_path)

def get_config(config_path):
    if not os.path.isfile(config_path):
        logging.critical("Could not find config file: %s", config_path)
        sys.exit(1)
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def get_config_entry(config, section, option, default=None):
    try:
        value = config.get(section, option)
        return value
    except configparser.NoOptionError:
        sys_error('=> config file section [%s] missing option %s'
                          % (section, option))
    except configparser.NoSectionError:
        sys_error('=> config file missing section %s' % section)
    return default

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
        except (configparser.NoOptionError, ConfigParser.NoSectionError):
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
    base_prefix = getattr(sys, "real_prefix", None) or getattr(sys, "base_prefix", None) or sys.prefix
    if sys.prefix == base_prefix:
        print("Remember to source bin/activate!")
        sys.exit(1)

def setup_logger(name, debug, log_path='/opt/himlarcli/', configfile='logging.yaml'):
    if not os.path.isfile(configfile):
        configfile = log_path + '/' + configfile
    with open(configfile, 'r') as stream:
        try:
            config = yaml.full_load(stream)
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
            print(e)
            print("Please check your log section in config.ini and logging.yaml")
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
        for k, v in i.items():
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
    logger.debug('=> download file {}'.format(target))
    target = get_abs_path(target)
    if not os.path.isfile(target):
        try:
            (filename, headers) = urllib.request.urlretrieve(source, target)
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
            response = urllib.request.urlopen(checksum_url)
        except urllib.error.HTTPError as exc:
            logger.debug('=> {}'.format(exc))
            logger.debug('=> unable to download checksum {}'.format(checksum_url))
            return None
        checksum_all = response.read().decode('utf-8')
        if checksum not in checksum_all:
            logger.debug("=> download checksum mismatch: %s" % checksum)
            return None
        else:
            logger.debug("=> download checksum match: %s" % checksum)
    return target

def compare_checksum(checksum, checksum_url, logger):
    """ Compare the checksum input with the checksum in the
        file. Will return True if the checksum match, False for mismatch or
        None for checksum file not found.
    """
    try:
        response = urllib.request.urlopen(checksum_url)
    except urllib.error.HTTPError as exc:
        logger.debug('=> {}'.format(exc))
        logger.debug('=> unable to download checksum {}'.format(checksum_url))
        return None
    try:
        checksum_all = response.read().decode("utf-8").split()[0]
    except:
        logger.debug("=> unable to parse checksum file: {}".format(checksum_url))
        checksum_all = None
    if checksum == checksum_all:
        logger.debug("=> checksum matched: {}".format(checksum))
        return True
    logger.debug("=> checksum mismatch: {} {}".format(checksum, checksum_url))
    return False

def checksum_file(file_path, checksum_type='sha256'):
    digest = getattr(hashlib, checksum_type)()
    digest.update(open(file_path,'rb').read())
    return digest.hexdigest()
