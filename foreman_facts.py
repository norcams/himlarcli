#!/usr/bin/env python
from himlarcli.parser import Parser
from himlarcli.printer import Printer
from himlarcli.foremanclient import Client

parser = Parser()
parser.toggle_show('dry-run')
parser.set_default_format('json')
options = parser.parse_args()
printer = Printer(options.format)

foreman = Client(options.config, options.debug)

hosts = options.hosts

mapping = {}

for host in hosts:
    fact = foreman.get_fact(host, options.fact)
    mapping[host] = fact

printer.output_dict(mapping)
