#!/bin/bash

source /opt/himlarcli/bin/activate

# default images
/opt/himlarcli/image.py update
sleep 60

# uio images
/opt/himlarcli/image.py update -i uio.yaml

