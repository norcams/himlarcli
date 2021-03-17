#!/bin/bash

region=$1
source /opt/himlarcli/bin/activate
/opt/himlarcli/demo.py delete --region $region --force --debug
