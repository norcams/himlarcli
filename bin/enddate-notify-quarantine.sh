#!/bin/bash
#
# DESCRIPTION: Send warning to admin/contact about projects in quarantine
#
# AUTHOR: trondham@uio.no
#

# Set proper path
PATH=/usr/bin
export PATH

# Set LC_TIME
LC_TIME=en_US.UTF-8
export LC_TIME

# Activate himlarcli virtualenv
source /opt/himlarcli/bin/activate

# Send warning mail
/opt/himlarcli/report.py quarantine --days 60 --days 30 --template notify/notify_enddate_quarantine.txt
