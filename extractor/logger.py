# encoding: utf-8

import sys
import logging


def create_nofile():
    logger = logging.getLogger('aqc')
    fmt = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s: %(message)s'
    format_str = logging.Formatter(fmt)
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(format_str)
    logger.addHandler(sh)
    return logger


logger = create_nofile()
