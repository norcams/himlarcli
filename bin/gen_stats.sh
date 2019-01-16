#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/stats.py legacy --quiet
/opt/himlarcli/stats.py compute --quiet

