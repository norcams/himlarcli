#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/stats.py legacy --quiet
/opt/himlarcli/stats.py compute --quiet

/opt/himlarcli/stats.py legacy --quiet -c /etc/himlarcli/config.ini.oldstats
/opt/himlarcli/stats.py compute --quiet -c /etc/himlarcli/config.ini.oldstats
