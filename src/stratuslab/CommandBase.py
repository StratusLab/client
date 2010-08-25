import socket
import sys
from optparse import OptionParser

from stratuslab.Exceptions import InputException
from stratuslab.Util import printError
from stratuslab.Util import runMethodByName

class CommandBase(object):
    
    def __init__(self):
        self.defaultDebugLevel = 3
        self.parser = OptionParser()
        self.parse()
        self.checkOptions()
        self._callAndHandleErrorsForCommands(self.doWork.__name__)

    def _callAndHandleErrorsForCommands(self, methodName, *args, **kw):
        
        if hasattr(self, 'config'):
            self.debugLevel = self.config.get('debug_level', self.defaultDebugLevel)
        else:
            self.debugLevel = self.defaultDebugLevel
        
        res = 0
        try:
            res = runMethodByName(methodName, *args, **kw)
        except ValueError, ex:
            sys.stderr.writelines('\nError: %s\n' % str(ex))
            sys.exit(3)
        except InputException, ex:
            printError('%s' % ex)
        except KeyboardInterrupt, ex:
            self.raiseOrDisplayError(ex)
        except SystemExit, ex:
            self.raiseOrDisplayError(ex)
        except socket.error, ex:
            self.raiseOrDisplayError(ex)
        except Exception, ex:
            self.raiseOrDisplayError(ex)
        return res
        
    def parse(self):
        pass

    def checkOptions(self):
        pass

    def checkArgumentsLength(self):
        pass

    def usageExitTooFewArguments(self):
        return self.parser.error('Too few arguments')

    def usageExitTooManyArguments(self):
        return self.parser.error('Too many arguments')

    def usageExitWrongNumberOfArguments(self):
        return self.parser.error('Wrong number of arguments')
    
    def raiseOrDisplayError(self, errorMsg):
        if self.debugLevel > 2:
            raise
        else:
            printError(errorMsg)
            