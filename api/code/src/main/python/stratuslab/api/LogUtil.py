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


class NoOpHandler(logging.Handler):
    """
    This handler acts as a 'no-op'.  It is a placeholder for the API
    to avoid having logging complain that there is no handler defined.
    This class is equivalent to the NullHandler that was introduced in
    Python 2.7; this class is only useful for supporting Python 2.6.
    """

    def __init__(self, level=logging.INFO):
        super(NoOpHandler, self).__init__(level=level)

    def emit(self, record):
        pass

    def handle(self, record):
        pass

    def createLock(self):
        return None


def get_console_logger(name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO, fmt=None):
    """
    Provides a logger that sends messages to the standard output (i.e.
    console) with the given name.  If the name is not supplied, the
    STRATUSLAB_API_LOGGER_NAME is used.  If the given logger already exists,
    then the configured console logger will be added to it.  The logging
    level is set to INFO if not supplied.  The default logging format
    will just emit the message.
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
    Provides a syslog-configured logger with the given name.  If the name
    is not supplied then STRATUSLAB_API_LOGGER_NAME is used.  If the given
    logger already exists, then the syslog handler will be added to it.
    The logging level will be set to INFO if not supplied.
    """

    logger = logging.getLogger(name)

    handler = SysLogHandler(address='/dev/log')
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def initialize_logger(logger_name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO):
    """
    Initializes the logger associated with the given name with a
    handler that will print nothing (NoOpHandler).  It removes any
    existing handlers and resets the logging level to INFO or to
    the level given.
    """
    logger = logging.getLogger(logger_name)
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(NoOpHandler(level=level))


def set_logger_level(logger_name=STRATUSLAB_API_LOGGER_NAME, level=logging.INFO):
    """
    Sets or resets the logging level for the named logger.  If the name
    is not supplied, then STRATUSLAB_API_LOGGER_NAME will be used.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)


#
# Initialize the logger with a 'no-op' handler.  Add another handler to actually
# push the logging messages somewhere.
#
initialize_logger()

