#!/bin/bash

source /opt/himlarcli/bin/activate
/opt/himlarcli/sync_owners.py sync
/opt/himlarcli/sync_owners.py purge

