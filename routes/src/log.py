"""
    This module handles logging
"""

import logging
import sys

from pythonjsonlogger import jsonlogger

logger = logging.getLogger()


def log_init():
    formatter = jsonlogger.JsonFormatter(
        '{"timestamp":%(asctime),"message":%(message),'
        '"function_name":%(funcName),"logger_name":%(name),'
        '"logger_level":%(levelname),"filename":%(filename),'
        '"line_number":%(lineno)'
    )

    logHandler = logging.StreamHandler(sys.stdout)

    logHandler.setFormatter(formatter)

    logger.addHandler(logHandler)
    logger.setLevel(logging.DEBUG)


