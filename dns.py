#!/usr/bin/env python
""" Setup designate DNS """

import utils
import re
from collections import OrderedDict
from himlarcli.keystone import Keystone
from himlarcli.designate import Designate
from himlarcli import utils as himutils
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.color import Color

himutils.is_virtual_env()

parser = Parser()
parser.set_autocomplete(True)
options = parser.parse_args()
printer = Printer(options.format)

kc= Keystone(options.config, debug=options.debug)
kc.set_domain(options.domain)
kc.set_dry_run(options.dry_run)
logger = kc.get_logger()

dns = Designate(options.config, debug=options.debug)

if options.action[0] == 'show':
    if options.dry_run:
        print('DRY-RUN: show')
    else:
        print('show')
elif options.action[0] == 'create':
    if options.dry_run:
        print('DRY-RUN: create')
    else:
        print('create')

# Description to be used for bulk imports
BULK_DESC = "BULK IMPORT FROM IANA"

# Helper function to get the diff between two arrays
def __diff_arrays(first, second):
    second = set(second)
    return [item for item in first if item not in second]


#--------------------------------------------------------------------
# Action functions
#--------------------------------------------------------------------
def action_blacklist_list():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    blacklists = designateclient.list_blacklists()
    if options.format == 'table':
        output = {}
        output['header'] = [
            'PATTERN',
            'DESCRIPTION',
            'ID',
        ]
        output['align'] = [
            'l',
            'l',
            'l',
        ]
        output['sortby'] = 0
        counter = 0

        if isinstance(blacklists, list):
            for b in blacklists:
                if not isinstance(b, dict):
                    b = b.to_dict()
                output[counter] = [
                    Color.fg.WHT + Color.bold + b['pattern'] + Color.reset,
                    Color.fg.GRN + b['description'] + Color.reset,
                    Color.dim + b['id'] + Color.reset,
                ]
                counter += 1
        printer.output_dict(output, sort=True, one_line=False)
    else:
        header = 'Blacklisted DNS domains (pattern, description, id)'
        printer.output_dict({'header': header})
        output = OrderedDict()
        outputs = ['pattern','description','id']
        if isinstance(blacklists, list):
            for b in blacklists:
                if not isinstance(b, dict):
                    b = b.to_dict()
                for out in outputs:
                    output[out] = b[out]
                printer.output_dict(objects=output, one_line=True, sort=False)

def action_blacklist_create():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    designateclient.create_blacklist(pattern=options.pattern, description=options.comment)

def action_blacklist_delete():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    designateclient.delete_blacklist(blacklist_id=options.this_id)

def action_blacklist_update():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    data = dict()
    if options.pattern:
        data['pattern'] = options.pattern
    if options.comment:
        data['description'] = options.comment
    designateclient.update_blacklist(blacklist_id=options.this_id, values=data)

def action_blacklist_show():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    res = designateclient.get_blacklist(blacklist_id=options.this_id)
    print()
    print("  Pattern: ...... %s" % res['pattern'])
    print("  Description: .. %s" % res['description'])
    print("  Created at: ... %s" % res['created_at'])
    print("  Updated at: ... %s" % res['updated_at'])
    print("  ID: ........... %s" % res['id'])
    print()

def action_tld_list():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    tlds = designateclient.list_tlds()
    if options.format == 'table':
        output = {}
        output['header'] = [
            'NAME',
            'DESCRIPTION',
            'ID',
        ]
        output['align'] = [
            'l',
            'l',
            'l',
        ]
        output['sortby'] = 0
        counter = 0
        if isinstance(tlds, list):
            for b in tlds:
                if not isinstance(b, dict):
                    b = b.to_dict()
                if b['description'] == 'BULK IMPORT FROM IANA':
                    desc_color = Color.fg.GRN
                else:
                    desc_color = Color.fg.blu
                output[counter] = [
                    Color.fg.ylw + Color.bold + b['name'] + Color.reset,
                    desc_color + b['description'] + Color.reset,
                    Color.dim + b['id'] + Color.reset,
                ]
                counter += 1
        printer.output_dict(output, sort=True, one_line=False)
    else:
        outputs = ['name','description','id']
        header = 'Top Level Domains (%s)' % (', '.join(outputs))
        printer.output_dict({'header': header})
        output = OrderedDict()
        if isinstance(tlds, list):
            for b in tlds:
                if not isinstance(b, dict):
                    b = b.to_dict()
                for out in outputs:
                    output[out] = b[out]
                printer.output_dict(objects=output, one_line=True, sort=False)

def action_tld_create():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    designateclient.create_tld(name=options.name, description=options.comment)

def action_tld_delete():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    designateclient.delete_tld(tld=options.this_id)

def action_tld_update():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    data = dict()
    if options.name:
        data['name'] = options.name
    if options.comment:
        data['description'] = options.comment
    designateclient.update_tld(tld=options.this_id, values=data)

def action_tld_show():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    tld = designateclient.get_tld(name=options.name)
    print()
    print("  Name: ......... %s" % tld['name'])
    print("  Description: .. %s" % tld['description'])
    print("  Created at: ... %s" % tld['created_at'])
    print("  Updated at: ... %s" % tld['updated_at'])
    print("  ID: ........... %s" % tld['id'])
    print()

def action_tld_import():
    designateclient = Designate(options.config, debug=options.debug, log=logger)
    global BULK_DESC

    # get all registered tlds
    existing = designateclient.list_tlds()
    registered_tlds = []
    if isinstance(existing, list):
        for this_tld in existing:
            if not isinstance(this_tld, dict):
                this_tld = this_tld.to_dict()
            if this_tld["description"] == BULK_DESC:
                registered_tlds.append(this_tld["name"]);

    # read the import file
    bulkfile = open(options.file, "r")
    iana_tlds = []
    for name in bulkfile:
        name = name.rstrip()
        name = name.lower()
        if re.match("^#.*", name):
            continue
        if re.match("^xn--", name):
            continue
        iana_tlds.append(name)

    # remove any registered "bulk import" tlds that aren't in the file
    remove_tlds = __diff_arrays(registered_tlds, iana_tlds)
    for name in remove_tlds:
        if options.debug:
            print("debug: removing tld: %s" % name)
        designateclient.delete_tld(tld=name)

    # add any new tlds from the file
    add_tlds = __diff_arrays(iana_tlds, registered_tlds)
    for name in add_tlds:
        if options.debug:
            print("debug: creating tld: %s" % name)
        designateclient.create_tld(name=name, description=BULK_DESC)


#--------------------------------------------------------------------
# Run local function with the same name as the action
#--------------------------------------------------------------------
action = locals().get('action_' + options.action)
if not action:
    himutils.sys_error("Function action_%s() not implemented" % options.action)
action()
