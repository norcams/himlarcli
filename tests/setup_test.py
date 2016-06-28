#!/usr/bin/env python

import os
import sys
import yaml
from himlarcli import utils

def main():
    # Test that virutalenv is setup
    if not os.environ.get('VIRTUAL_ENV'):
        print "Warning: VIRTUAL_ENV is not set!"
        print "Running from /opt/himlarcli"

    # Test logging config
    log_config_path = utils.get_abs_path('logging.yaml')
    if not os.path.isfile(log_config_path):
        print "Could not load logging config from %s" % log_config_path
        sys.exit(1)

    # Config file test
    config_path = '/etc/himlarcli/config.ini'
    if os.path.isfile(config_path):
        config_file(config_path)
    else:
        print "Warning: No default config file found at %s" % config_path

    # Test that requirements.txt modules are installed
    modules_file = utils.get_abs_path('tests/modules.txt')
    with open(modules_file) as f:
        modules = f.read().splitlines()
    try:
        map(__import__, modules)
    except ImportError as e:
        print e
        sys.exit(1)

def config_file(config_path):
    config_template = utils.get_abs_path('tests/config.yaml')
    config = utils.get_config(config_path)
    with open(config_template) as template:
        try:
            tests = yaml.load(template)
        except yaml.YAMLError as e:
            print e
    for section, options in tests.iteritems():
        if not config.has_section(section):
            print "Missing section [%s]" % section
            sys.exit(1)
        for i in options:
            if not config.has_option(section, i):
                print "Missing option %s in section [%s]" % (i,section)
                sys.exit(1)

if __name__ == "__main__":
    main()
