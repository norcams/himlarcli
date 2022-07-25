#!/usr/bin/env python

from himlarcli import utils

logger = utils.setup_logger(__name__, False, './')
logger.debug('rotating logs')
logger.doRollover()
