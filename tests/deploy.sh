#!/bin/bash

# Run this test on deployment

if [ "$#" -ne 1 ]; then
  install_dir='/opt/himlarcli'
else
  install_dir=$1
fi

source ${install_dir}/bin/activate
${install_dir}/tests/setup_test.py
${install_dir}/tests/logtest.py
