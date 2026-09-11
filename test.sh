#!/bin/bash

# Simple script to run pylint test. This is the same tests travis use.

# request_specs.py is skipped: it needs the nova package, which is not in
# requirements.txt (see the commented-out nova pin there)
find . -maxdepth 1 -type f  \( -iname "*.py" ! -iname "setup.py" ! -iname "request_specs.py" \)  | xargs pylint -E
