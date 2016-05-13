#!/usr/bin/python
import argparse
from foremancli.client import Client

parser = argparse.ArgumentParser(description='Toggle rebuild host in foreman')
parser.add_argument('-c',
                     dest='config',
                     metavar='config.ini',
                     action='store',
                     default='config.ini',
                     help='path to ini file with config')
parser.add_argument('host',
                     metavar='FQDN',
                     type=str,
                     nargs='+',
                     help='host to rebuild')
options = parser.parse_args()

foreman = Client(options.config)

for host in options.host:
    foreman.set_host_build(host)
