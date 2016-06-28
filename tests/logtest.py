#!/usr/bin/env python

import os
from himlarcli import utils

def main():
    logger = utils.setup_logger('test', debug=True)
    logger.debug('This should be both in logfile and console')

if __name__ == "__main__":
    main()
