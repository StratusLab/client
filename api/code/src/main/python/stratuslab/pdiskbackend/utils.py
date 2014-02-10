
import sys
import logging
import logging.handlers

from stratuslab.pdiskbackend import defaults

__all__ = ['abort',
           'Logger',
           'EXITCODE_PDISK_OP_FAILED']

verbosity = 0
EXITCODE_PDISK_OP_FAILED = 2

def abort(msg):
    print >> sys.stderr, "Persistent disk operation failed:\n%s" % msg
    sys.exit(EXITCODE_PDISK_OP_FAILED)

class Logger(object):
    def __init__(self, configHolder):
        self._log_file = configHolder.get(defaults.CONFIG_MAIN_SECTION, 'log_file')
        self._verbosity = configHolder.verbosity
        self._logger = self._get_loger()

    def debug(self, level, msg):
        if level <= self._verbosity:
            if level == 0:
                self._logger.info(msg)
            else:
                self._logger.debug(msg)

    def _get_loger(self):
        logging_source = 'stratuslab-pdisk'
        logger = logging.getLogger(logging_source)
        logger.setLevel(logging.DEBUG)
        
        # fmt=logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)
        
        logfile_handler = None
        if self._log_file:
            try:
                logfile_handler = logging.handlers.RotatingFileHandler(self._log_file,
                                                                       'a', 100000, 10)
                logfile_handler.setLevel(logging.DEBUG)
                logfile_handler.setFormatter(fmt)
                logger.addHandler(logfile_handler)
            except ValueError:
                abort("Invalid value specified for 'log_file' (section %s)" %
                                                    defaults.CONFIG_MAIN_SECTION)
        
        if logfile_handler == None or not self._log_file:
            # Use standard log destination in case a log file is not defined
            syslog_handler = logging.handlers.SysLogHandler('/dev/log')
            syslog_handler.setLevel(logging.WARNING)
            logger.addHandler(syslog_handler)
    
        return logger
