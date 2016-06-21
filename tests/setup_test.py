#!/usr/bin/env python

import os
import sys
import yaml
from himlarcli import utils

def main():
    # Test that virutalenv is setup
    if not os.environ.get('VIRTUAL_ENV'):
        print "Please make sure environment variable VIRTUAL_ENV is set!"
        sys.exit(1)

    # Config file test
    config_path = '/etc/himlarcli/config.ini'
    if os.path.isfile(config_path):
        config_file(config_path)
    else:
        print "No default config file found at %s" % config_path

    # Test that requirements.txt modules are installed
    install_dir = os.environ['VIRTUAL_ENV']
    with open(install_dir + '/tests/modules.txt') as f:
        modules = f.read().splitlines()
    try:
        map(__import__, modules)
    except ImportError as e:
        print e
        sys.exit(1)

def config_file(config_path):
    install_dir = os.environ['VIRTUAL_ENV']
    config = utils.get_config(config_path)
    with open(install_dir + '/tests/config.yaml') as stream:
        try:
            tests = yaml.load(stream)
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
