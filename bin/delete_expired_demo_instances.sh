#!/bin/bash

region=$1
source /opt/himlarcli/bin/activate
/opt/himlarcli/demo.py delete_expired_instance -d 90 --region $region --force --debug 
