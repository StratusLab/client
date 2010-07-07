import os
import sys
import logging
import uuid as uuidModule

timeformat = '%Y-%m-%d %H:%M:%S'
defaultConfigSection = 'stratuslab'

def configureLogger():
    filename = os.path.abspath('%s/../stratuslab.log' %
        os.path.abspath(os.path.dirname(__file__)))
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s %(message)s',
                        filename=filename)

def removeLogger(handler):
    logger = logging.getLogger()
    logger.removeHandler(handler)

def redirectStd2Logger():
    configureLogger()
    sys.stderr = StdOutWithLogger('stderr')
    stdout = StdOutWithLogger('stdout')
    sys.stdout = stdout
    return

def resetStdFromLogger():
    sys.stdout = sys.stdout._std
    sys.stderr = sys.stderr._std

def whoami():
    return sys._getframe(1).f_code.co_name

def fileGetContents(filename):
    fd = open(filename, 'rb')
    content = fd.read()
    fd.close()
    return content

def filePutContents(filename, data):
    fd = open(filename, 'wb')
    fd.write(data)
    fd.close()

class StdOutWithLogger:
    def __init__(self,std):
        if std == 'stdout':
            self._std = sys.stdout
            self.logType = 'out'
        elif std == 'stderr':
            self._std = sys.stderr
            self.logType = 'err'
        else:
            raise ValueError('Unknown std type: %s' % std)

    def writelines(self, msgs):
        # Test if msgs is a list or not
        try:
            msgs.append('')
        except AttributeError:
            # It's probably a string, so we write it directly
            self.write(msgs + '\n')
            return
        for msg in msgs:
            self.write(msg)
        return

    def write(self, string):
        _string = unicode(string).encode('utf-8')
        self._std.write(_string)
        if string == '.':
            return
        if self.logType == 'out':
            logging.info(_string)
        else:
            logging.error(_string)
        return

    def flush(self):
        self._std.flush()

def getHomeDirectory():
    if (sys.platform == "win32"):
        if (os.environ.has_key("HOME")):
            return os.environ["HOME"]
        elif (os.environ.has_key("USERPROFILE")):
            return os.environ["USERPROFILE"]
        else:
            return "C:\\"
    else:
        if (os.environ.has_key("HOME")):
            return os.environ["HOME"]
        else:
            # No home directory set
            return ""

def uuid():
    '''Generates a unique ID.'''
    return str(uuidModule.uuid4())

def validConfiguration(config):
    if not config.has_section(defaultConfigSection):
        raise ValueError('Invalid configuration')
        
