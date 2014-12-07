
import sys
import logging

import stratuslab.api.LogUtil as LogUtil
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Util import printDetail

__all__ = ['abort',
           'EXITCODE_PDISK_OP_FAILED']

EXITCODE_PDISK_OP_FAILED = 2


def abort(msg):
    print >> sys.stderr, "Persistent disk operation failed:\n%s" % msg
    sys.exit(EXITCODE_PDISK_OP_FAILED)


def initialize_logger(log_direction, verbosity):
    level = (0 == verbosity) and logging.INFO or logging.DEBUG
    if 'console' == log_direction:
        return LogUtil.get_console_logger(level=level)
    elif 'syslog' == log_direction:
        return LogUtil.get_syslog_logger(level=level)
    else:
        raise ConfigurationException('Wrong value for log_direction: %s' % log_direction)


def print_detail(msg, level=0):
    printDetail(msg, verboseThreshold=level)
