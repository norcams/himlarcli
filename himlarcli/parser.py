import argparse
import inspect
import os
from himlarcli.printer import Printer
from himlarcli import utils
import sys
from pydoc import locate

class Parser(object):

    """ Default options. If we use actions these will be added to them as well. """
    SHOW = dict()
    SHOW['config'] = True
    SHOW['debug'] = True
    SHOW['dry-run'] = True
    SHOW['format'] = True

    FORMATTER = dict()
    FORMATTER['text'] = argparse.RawTextHelpFormatter
    FORMATTER['raw'] = argparse.RawDescriptionHelpFormatter
    FORMATTER['arg'] = argparse.ArgumentDefaultsHelpFormatter

    ACTION_TITLE = 'valid actions'
    ACTION_DESC = 'Use -h for each action'

    def __init__(self, name=None, description=None, autoload=True, formatter='arg'):
        if formatter not in ['raw', 'text', 'arg']:
            formatter = 'arg'
        if not name: #use basename from calling script
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            self.name = os.path.splitext(os.path.basename(module.__file__))[0]
        self.opt_args = {}
        self.actions = {}
        self.desc = description
        self.formater = self.FORMATTER[formatter]
        self.parser = None
        self.subparser = None
        self.parsers = None
        if autoload:
            self.__autoload()

    def add_opt_args(self, opt_args):
        self.opt_args = opt_args

    def add_actions(self, actions):
        self.actions = actions

    def toggle_show(self, option):
        if option in self.SHOW and self.SHOW[option]:
            self.SHOW[option] = False
        elif option in self.SHOW and not self.SHOW[option]:
            self.SHOW[option] = True

    def update_default(self, name, value):
        if name in self.opt_args:
            self.opt_args[name]['default'] = value

    def parse_args(self):
        self.__setup_parser()
        self.__add_config()
        self.__add_debug()
        self.__add_dry_run()
        self.__add_format()
        self.__add_opt_args()
        return self.parser.parse_args()

    # ------------------------------- PRIVATE FUNCTIONS ------------------------
    def __setup_parser(self):
        self.parser = argparse.ArgumentParser(description=self.desc,
                                              formatter_class=self.formater)
        if self.actions:
            self.__add_actions(self.actions)

    """
    Load parser config from yaml.
    """
    def __autoload(self):
        parser_config = utils.load_config('config/parser/%s.yaml' % self.name)
        if 'desc' in parser_config:
            self.desc = parser_config['desc']
        if 'actions' in parser_config:
            self.actions = parser_config['actions']
        if 'opt_args' in parser_config:
            self.opt_args = parser_config['opt_args']

    def __add_actions(self, actions):
        self.subparser = self.parser.add_subparsers(title=self.ACTION_TITLE,
                                                    help=self.ACTION_DESC)
        self.parsers = dict()
        for action, desc in actions.iteritems():
            self.parsers[action] = self.subparser.add_parser(action,
                                                             description=desc,
                                                             formatter_class=self.formater)
            self.parsers[action].set_defaults(action=action)

    def __add_config(self):
        if self.SHOW['config'] and self.parsers:
            for parser in self.parsers.itervalues():
                parser.add_argument('-c',
                                    dest='config',
                                    metavar='config.ini',
                                    action='store',
                                    default='/etc/himlarcli/config.ini',
                                    help='path to ini file with config')
        elif self.SHOW['config']:
            self.parser.add_argument('-c',
                                     dest='config',
                                     metavar='config.ini',
                                     action='store',
                                     default='/etc/himlarcli/config.ini',
                                     help='path to ini file with config')

    def __add_debug(self):
        if self.SHOW['debug'] and self.parsers:
            for parser in self.parsers.itervalues():
                parser.add_argument('--debug',
                                    dest='debug',
                                    action='store_const',
                                    const=True,
                                    default=False,
                                    help='verbose debug mode')
        elif self.SHOW['debug']:
            self.parser.add_argument('--debug',
                                     dest='debug',
                                     action='store_const',
                                     const=True,
                                     default=False,
                                     help='verbose debug mode')

    def __add_dry_run(self):
        if self.SHOW['dry-run'] and self.parsers:
            for parser in self.parsers.itervalues():
                parser.add_argument('--dry-run',
                                    dest='dry_run',
                                    action='store_const',
                                    const=True,
                                    default=False,
                                    help='dry run this script')
        elif self.SHOW['dry-run']:
            self.parser.add_argument('--dry-run',
                                     dest='dry_run',
                                     action='',
                                     const=True,
                                     default=False,
                                     help='dry run this script')
    def __add_format(self):
        valid_format = Printer.VALID_OPTIONS
        if self.SHOW['format'] and self.parsers:
            for parser in self.parsers.itervalues():
                parser.add_argument('--format',
                                    dest='format',
                                    choices=valid_format,
                                    type=str,
                                    default='text',
                                    help='output format')
        elif self.SHOW['format']:
            self.parser.add_argument('--format',
                                     dest='format',
                                     choices=self.FORMATS,
                                     type=str,
                                     default='text',
                                     help='output format')

    """
    Arg options:
        - sub: add this arg only to this sub action
        - name: arg name. E.G. '-n'
        - dest: variable name to store the result in
        - default: default value
        - help: help text
        - choices: valid options for this choice
        - metavar: help text example variable name
        - action: store for variable and store_const for boolean
        - required: boolean
        - type: string value of type
    """
    def __add_opt_args(self):
        for name, arg in self.opt_args.iteritems():
            if not 'dest' in arg:
                print 'missing dest in opt_args'
                continue
            if 'type' in arg:
                # Use locate to find buildt-in types
                arg['type'] = locate(arg['type'])
            # Find the parse to use (some, all, or default parser)
            parsers = dict()
            if 'sub' in arg: # one or more sub parsers
                if isinstance(arg['sub'], list):
                    for i in arg['sub']:
                        if i in self.parsers:
                            parsers[i] = self.parsers[i]
                elif arg['sub'] in self.parsers:
                    parsers[arg['sub']] = self.parsers[arg['sub']]
            elif self.parsers: # add to all sub parsers
                parsers = self.parsers
            else: # no subparsers in use
                parsers[0] = self.parser
            for parser in parsers.itervalues():
                if 'sub' in arg:
                    del arg['sub']
                self.__add_argument(parser=parser, name=name, **arg)

    @staticmethod
    def __add_argument(parser, name, **kwargs):
        if 'dest' not in kwargs:
            print 'missing dest in opt_args'
            sys.exit(1)
        kwargs['action'] = kwargs['action'] if 'action' in kwargs else 'store'
        kwargs['help'] = kwargs['help'] if 'help' in kwargs else kwargs['dest']
        kwargs['metavar'] = kwargs['metavar'] if 'metavar' in kwargs else kwargs['dest']
        kwargs['const'] = True if kwargs['action'] == 'store_const' else None
        parser.add_argument(name, **kwargs)
