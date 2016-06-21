#!/usr/bin/env python

import os
from himlarcli import logger

install_dir = os.environ['VIRTUAL_ENV']
logger = logger.setup_logger('test',
                             debug=True,
                             log_path=install_dir + '/',
                             configfile=install_dir + '/logging.yaml')

logger.debug('This should be both in logfile and console')

sys.exit(1)
