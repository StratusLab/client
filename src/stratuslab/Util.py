from com.sixsq.slipstream.exceptions.Exceptions import ConfigurationFileError
import logging
import os
import sys
import uuid as uuidModule

timeformat = '%Y-%m-%d %H:%M:%S'

def configureLogger():
    filename=os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])),'slipstream.log')
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

def getConfigFileName():
    ''' Look for the configuration file in the following order:
        1- local directory
        2- installation location
        3- calling module location
    '''
    filename = 'slipstream.client.conf'
    configFilename = os.path.join(os.getcwd(),filename)
    if os.path.exists(configFilename):
        return configFilename
    configFilename = os.path.join(getInstallationLocation(),filename)
    if not os.path.exists(configFilename):
        configFilename = os.path.join(os.path.dirname(sys.argv[0]),filename)
    if not os.path.exists(configFilename):
        raise ConfigurationFileError('Failed to find the configuration file: ' + configFilename)
    return configFilename

def getInstallationLocation():
    ''' Look for the installation location in the following order:
        1- SLIPSTREAM_HOME env var if set
        2- Default target directory, if exists (/opt/slipstream/src)
        3- Base module: __file__/../../.., since the util module is namespaced
    '''
    slipstreamDefaultDirName = os.path.join(os.sep,'opt','slipstream','client','src')
    # Relative to the src dir.  We do this to avoid importing a module, since util
    # should have a minimum of dependencies
    slipstreamDefaultRelativeDirName = os.path.join(os.path.dirname(__file__),'..','..','..')
    if os.environ.has_key('SLIPSTREAM_HOME'):
        slipstreamHome = os.environ['SLIPSTREAM_HOME']
    elif os.path.exists(slipstreamDefaultDirName):
        slipstreamHome = slipstreamDefaultDirName
    else:
        slipstreamHome = slipstreamDefaultRelativeDirName
    return slipstreamHome

def uuid():
    '''Generates a unique ID.'''
    return str(uuidModule.uuid4())
