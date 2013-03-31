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

import sys
import logging
from logging import StreamHandler
from logging.handlers import SysLogHandler


def get_console_logger(name=__name__, level=logging.INFO, fmt=None):
    """
    Provides a logger that sends messages to the standard output (i.e.
    console) with the given name.  If the name is not supplied, the
    __name__ for this file is used.  If the given logger already exists,
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


def get_syslog_logger(name=__name__, level=logging.INFO):
    """
    Provides a syslog-configured logger with the given name.  If the name
    is not supplied then __name__ for this file is used.  If the given
    logger already exists, then the syslog handler will be added to it.
    The logging level will be set to INFO if not supplied.
    """

    logger = logging.getLogger(name)

    handler = SysLogHandler(address='/dev/log')
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger

