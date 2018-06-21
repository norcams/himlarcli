#!/bin/bash

# Simple script to run pylint test. This is the same tests travis use.

find . -maxdepth 1 -type f  \( -iname "*.py" ! -iname "setup.py" \)  | xargs pylint -E
