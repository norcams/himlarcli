#!/bin/bash
#
# DESCRIPTION: Delete projects that have been in quarantine for X days
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

# Delete projects
for project in $(/opt/himlarcli/report.py quarantine --days 90 --list | awk '{print $2}'); do
    /opt/himlarcli/project.py --force delete $project
done
