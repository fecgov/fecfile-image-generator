"""
    This module handles logging
"""

import logging
import sys

from pythonjsonlogger import jsonlogger

logger = logging.getLogger()


def log_init():
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(messages)s %(funcName)s %(name)s %(levelname)s %(filename)s %(lineno)s'
    )

    logHandler = logging.StreamHandler(sys.stdout)

    logHandler.setFormatter(formatter)

    logger.addHandler(logHandler)
    logger.setLevel(logging.DEBUG)
