#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/rotate_log.py

gzip /opt/himlarcli/logs/himlar.log.20*

