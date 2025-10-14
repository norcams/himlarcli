#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/check_services.py
/opt/himlarcli/check_services.py -c /etc/himlarcli/config.ini.oldstats
