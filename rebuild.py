#!/usr/bin/env python
import utils
import sys
from himlarcli.foremanclient import Client

desc = 'Toggle rebuild host in foreman'
options = utils.get_options(desc)

foreman = Client(options.config, options.debug)

for host in options.host:
    foreman.set_host_build(host)
