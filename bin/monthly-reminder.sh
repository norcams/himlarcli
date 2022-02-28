#!/bin/bash
#
# DESCRIPTION: Send a reminder to project owners and members about
#              resources they are currently using in NREC. Activated
#              by crond and will only run if this is the first weekday
#              of the month.
#
# AUTHOR: trondham@uio.no
#

# Set proper path
PATH=/usr/bin
export PATH

# Set LC_TIME
LC_TIME=en_US.UTF-8
export LC_TIME

# Only run if this is the first weekday of month
day_of_month=$(date +%d)
day_name=$(date +%a)
if [ $day_name == 'Mon' -a $day_of_month -eq 1  ]; then
    :
elif [ $day_name == 'Mon' -a $day_of_month -eq 2  ]; then
    :
elif [ $day_name == 'Mon' -a $day_of_month -eq 3  ]; then
    :
elif [ $day_name == 'Tue' -a $day_of_month -eq 1  ]; then
    :
elif [ $day_name == 'Wed' -a $day_of_month -eq 1  ]; then
    :
elif [ $day_name == 'Thu' -a $day_of_month -eq 1  ]; then
    :
elif [ $day_name == 'Fri' -a $day_of_month -eq 1  ]; then
    :
else
    exit 0
fi

# Run monthly reminder
source /opt/himlarcli/bin/activate
/opt/himlarcli/report.py mail --template /opt/himlarcli/notify/resource_report.txt --subject 'Your NREC Resources (Monthly Reminder)'
