import os
import sys
import logging
import logging.config
import warnings
import yaml

def setup_logger(name, debug,
                 log_path = '/opt/himlarcli/',
                 configfile = 'logging.yaml'):
    with open(log_path + configfile, 'r') as stream:
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
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        #print "%s: loglevel %s" % (name, logging.DEBUG)
    return logger
