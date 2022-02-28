#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/report.py mail --template /opt/himlarcli/notify/resource_report.txt --subject 'Your NREC Resources (Monthly Reminder)'
