#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This module provides standard logging functions for the StratusLab
API.  It provides convenience functions that allow a console or
syslog logger to be obtained easily.  It also allows the special
'stratuslab.api' logger to be obtained and modified.

Note that the 'stratuslab.api' logger is configured by default to
do nothing.  If you want to enable the logging, then this module
should be imported and the appropriate handlers added to the logger.
This can be done easily with the following:

>>> import stratuslab.api.LogUtil as LogUtil
>>> LogUtil.get_console_logger()
>>> ...
>>> LogUtil.set_logger_level(logging.DEBUG)

Name of the logger instance used throughout the StratusLab API.  The
logger associated with this name should only be manipulated through
the utility functions defined here.
"""

import sys
import logging
from logging import StreamHandler
from logging.handlers import SysLogHandler


STRATUSLAB_API_LOGGER_NAME = 'stratuslab.api'


class NullHandler(logging.Handler):
    """
    This handler acts as a 'no-op'.  It is a placeholder for the API
    to avoid having logging complain that there is no handler defined.
    This class is used only for Python 2.6 because in Python 2.7 such
    a class was defined in the standard distribution.
    """

    lock = None

    def __init__(self, level=logging.INFO):
        # NOTE: super cannot be used here because it will fail on
        # python 2.6, which uses old style classes for logging.
        logging.Handler.__init__(self, level=level)

    def emit(self, record):
        pass

    def handle(self, record):
        pass

    def createLock(self):
        return self.lock


def get_console_logger(name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO, fmt=None):
    """
    Provides a logger that sends messages to the standard output (i.e.
    console) with the given name.  If the name is not supplied, the
    STRATUSLAB_API_LOGGER_NAME is used.  If the given logger already
    exists, then the configured console logger will be added to it.
    The logging level is set to INFO if not supplied.  The default
    logging format will just emit the message.
    """

    logger = logging.getLogger(name)

    handler = StreamHandler(sys.stdout)
    if not fmt:
        fmt = logging.Formatter(fmt=None, datefmt=None)
    handler.setFormatter(fmt)

    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def get_syslog_logger(name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO):
    """
    Provides a syslog-configured logger with the given name.  If the
    name is not supplied then STRATUSLAB_API_LOGGER_NAME is used.  If
    the given logger already exists, then the syslog handler will be
    added to it.  The logging level will be set to INFO if not
    supplied.
    """

    logger = logging.getLogger(name)

    if sys.platform.startswith('linux'):
        address = '/dev/log'
    elif sys.platform == 'darwin':
        address = '/var/run/syslog'
    else:
        raise Exception("Don't know syslog facility on %s" % sys.platform)

    handler = SysLogHandler(address=address)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def initialize_logger(logger_name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO):
    """
    Initializes the logger associated with the given name with a
    handler that will print nothing (NullHandler).  It removes any
    existing handlers and resets the logging level to INFO or to the
    level given.
    """
    logger = logging.getLogger(logger_name)
    for h in list(logger.handlers):
        logger.removeHandler(h)

    try:
        h = logging.NullHandler(level=level)  # for python 2.7.x
    except AttributeError:
        h = NullHandler(level=level)  # for python 2.6.x

    logger.addHandler(h)


def set_logger_level(logger_name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO):
    """
    Sets or resets the logging level for the named logger.  If the
    name is not supplied, then STRATUSLAB_API_LOGGER_NAME will be
    used.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)


def critical(msg):
    """
    Convenience method for logging critical messages to the StratusLab
    API logger.
    """
    logger = logging.getLogger(STRATUSLAB_API_LOGGER_NAME)
    logger.critical(msg)


def error(msg):
    """
    Convenience method for logging error messages to the StratusLab
    API logger.
    """
    logger = logging.getLogger(STRATUSLAB_API_LOGGER_NAME)
    logger.error(msg)


def warning(msg):
    """
    Convenience method for logging warning messages to the StratusLab
    API logger.
    """
    logger = logging.getLogger(STRATUSLAB_API_LOGGER_NAME)
    logger.warning(msg)


def info(msg):
    """
    Convenience method for logging info messages to the StratusLab API
    logger.
    """
    logger = logging.getLogger(STRATUSLAB_API_LOGGER_NAME)
    logger.info(msg)


def debug(msg):
    """
    Convenience method for logging debug messages to the StratusLab
    API logger.
    """
    logger = logging.getLogger(STRATUSLAB_API_LOGGER_NAME)
    logger.debug(msg)


def exception(msg):
    """
    Convenience method for logging exception messages to the
    StratusLab API logger.  This method should only be called from
    exception handlers.  The exception information is included in the
    message.
    """
    logger = logging.getLogger(STRATUSLAB_API_LOGGER_NAME)
    logger.exception(msg)


#
# Initialize the logger with a 'no-op' handler.  Add another handler
# to actually push the logging messages somewhere.
#
initialize_logger()
