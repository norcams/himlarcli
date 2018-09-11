#!/usr/bin/env python
import utils
import sys
from himlarcli.foremanclient import Client
from himlarcli.sensu import Sensu

desc = 'Toggle rebuild host in foreman'
options = utils.get_options(desc)

foreman = Client(options.config, options.debug)
sensu = Sensu(options.config, debug=options.debug)

for host in options.host:
    sensu.silence_host(host, expire=3600)
    foreman.set_host_build(host)
