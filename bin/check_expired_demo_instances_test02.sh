#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/demo.py expired -d 60 -t notify/demo-notify-expired-instances-30dleft.txt --region test02
/opt/himlarcli/demo.py expired -d 75 -t notify/demo-notify-expired-instances-15dleft.txt --region test02
/opt/himlarcli/demo.py expired -d 89 -t notify/demo-notify-expired-instances-1dleft.txt --region test02
