#!/usr/bin/env python

import logging
from himlarcli import utils

# config logger with logging.yaml
logger = utils.setup_logger(__name__, False, './')
logger.debug('rotating logs')

# rotate file handler
for handler in logging.getLogger().handlers:
    if handler.name == 'file':
        handler.doRollover()
