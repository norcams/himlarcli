#!/bin/bash
#
# DESCRIPTION: Put projects into quarantine, if they have reached
#              their end date
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

# Quarantine projects
for project in $(/opt/himlarcli/report.py enddate --days 0 --list | awk '{print $2}'); do
    /opt/himlarcli/project.py quarantine --reason enddate -m --template notify/notify_enddate_after.txt $project
done
