import getopt
import sys
import os.path
import argparse



def get_options(desc, config=True, debug=True, dry_run=False, hosts='+'):
    parser = argparse.ArgumentParser(description=desc)
    if debug:
        parser.add_argument('-d',
                            dest='debug',
                            action='store_const',
                            const=True,
                            default=False,
                            help='verbose debug mode')
    if config:
        parser.add_argument('-c',
                            dest='config',
                            metavar='config.ini',
                            action='store',
                            default='/etc/himlarcli/config.ini',
                            help='path to ini file with config')
    if dry_run:
        parser.add_argument('--dry-run',
                            dest='dry_run',
                            action='store_const',
                            const=True,
                            default=False,
                            help='dry run script')
    if hosts:
        parser.add_argument('host',
                            metavar='FQDN',
                            type=str,
                            nargs=hosts,
                            help='nova compute host')
    return parser.parse_args()

def get_host_action_options(desc, actions, hosts=True, config=True, debug=True):
    parser = argparse.ArgumentParser(description=desc)
    if debug:
        parser.add_argument('-d',
                            dest='debug',
                            action='store_const',
                            const=True,
                            default=False,
                            help='verbose debug mode')
    if config:
        parser.add_argument('-c',
                            dest='config',
                            metavar='config.ini',
                            action='store',
                            default='/etc/himlarcli/config.ini',
                            help='path to ini file with config')
    if hosts:
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

def get_node_action_options(desc, actions, nodes=True, dry_run=False, config=True, debug=True):
    parser = argparse.ArgumentParser(description=desc)
    if debug:
        parser.add_argument('-d',
                            dest='debug',
                            action='store_const',
                            const=True,
                            default=False,
                            help='verbose debug mode')
    if config:
        parser.add_argument('-c',
                            dest='config',
                            metavar='config.ini',
                            action='store',
                            default='/etc/himlarcli/config.ini',
                            help='path to ini file with config')
    if dry_run:
        parser.add_argument('--dry-run',
                            dest='dry_run',
                            action='store_const',
                            const=True,
                            default=False,
                            help='dry run script')
    if nodes:
        parser.add_argument('-n',
                            dest='node',
                            metavar='nodename',
                            action='store',
                            help='nodename (mandatory for some actions)',
                            default=None)
    parser.add_argument('action',
                        metavar='actions',
                        choices=actions,
                        type=str,
                        nargs=1,
                        help='|'.join(actions))
    return parser.parse_args()

def get_action_options(desc, actions, dry_run=False, config=True, debug=True, opt_args={}):
    parser = argparse.ArgumentParser(description=desc)
    if debug:
        parser.add_argument('-d',
                            dest='debug',
                            action='store_const',
                            const=True,
                            default=False,
                            help='verbose debug mode')
    if config:
        parser.add_argument('-c',
                            dest='config',
                            metavar='config.ini',
                            action='store',
                            default='/etc/himlarcli/config.ini',
                            help='path to ini file with config')
    if dry_run:
        parser.add_argument('--dry-run',
                            dest='dry_run',
                            action='store_const',
                            const=True,
                            default=False,
                            help='dry run script')
    for name, arg in opt_args.iteritems():
        if not 'dest' in arg:
            print 'missing dest in opt_args'
            continue
        if not 'default' in arg:
            arg['default'] = False
        if not 'action' in arg:
            arg['action'] = 'store'
        if not 'help' in arg:
            arg['help'] = arg['dest']
        if not 'metavar' in arg:
            arg['metavar'] = arg['dest']
        if not 'const' in arg:
            arg['const'] = None
        parser.add_argument(name,
                            dest=arg['dest'],
                            action=arg['action'],
                            default=arg['default'],
                            metavar=arg['metavar'],
                            const=arg['const'],
                            help=arg['help'])
    parser.add_argument('action',
                        metavar='actions',
                        choices=actions,
                        type=str,
                        nargs=1,
                        help='|'.join(actions))
    return parser.parse_args()
