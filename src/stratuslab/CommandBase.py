import socket
import sys
from optparse import OptionParser

from stratuslab.Exceptions import InputException
from stratuslab.Exceptions import NetworkException
from stratuslab.Util import printError
from stratuslab.Util import runMethodByName

class CommandBase(object):
    
    def __init__(self):
        self.verboseLevel = 0
        self.parser = None
        self._setParserAndParse()
        self.checkOptions()
        self._callAndHandleErrors(self, self.doWork.__name__)

    def _setParserAndParse(self):
        self.parser = OptionParser()
        self.parser.add_option('-v', '--verbose', dest='verboseLevel',
                help='Verbose level. Add more to get more details.',
                action='count', default=self.verboseLevel)
        self.parse()
        self.verboseLevel = self.options.verboseLevel
        
    def _callAndHandleErrors(self, methodName, *args, **kw):
        
        res = 0
        try:
            res = runMethodByName(methodName, *args, **kw)
        except ValueError, ex:
            sys.stderr.writelines('\nError: %s\n' % str(ex))
            sys.exit(3)
        except NetworkException, ex:
            printError('%s' % ex)
        except InputException, ex:
            printError('%s' % ex)
        except KeyboardInterrupt, ex:
            self.raiseOrDisplayError(ex)
        except SystemExit, ex:
            self.raiseOrDisplayError(ex)
        except socket.error, ex:
            self.raiseOrDisplayError('Network error: %s' % ex)
        except socket.gaierror, ex:
            self.raiseOrDisplayError('Network error: %s' % ex)
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
        if self.verboseLevel > 0:
            raise
        else:
            printError(errorMsg)
