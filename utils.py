import getopt
import sys
import os.path
import argparse

def get_host_options(desc, config=True, hosts='+'):
    parser = argparse.ArgumentParser(description=desc)
    if config:
        parser.add_argument('-c',
                            dest='config',
                            metavar='config.ini',
                            action='store',
                            default='config.ini',
                            help='path to ini file with config')
    parser.add_argument('host',
                        metavar='FQDN',
                        type=str,
                        nargs=hosts,
                        help='nova compute host')
    return parser.parse_args()

def get_action_options(desc, actions, config=True):
    parser = argparse.ArgumentParser(description=desc)
    if config:
        parser.add_argument('-c',
                            dest='config',
                            metavar='config.ini',
                            action='store',
                            default='config.ini',
                            help='path to ini file with config')
    parser.add_argument('host',
                        metavar='FQDN',
                        action='store',
                        help='nova compute host')
    parser.add_argument('action',
                        metavar='actions',
                        choices=actions,
                        type=str,
                        nargs=1,
                        help='|'.join(actions))
    return parser.parse_args()
