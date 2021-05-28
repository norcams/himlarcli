#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/security_group.py --list -y > /opt/himlarcli/reports/security_groups/$(date +"%Y-%m-%d").txt
