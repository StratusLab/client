import sys
from stratuslab.Util import printError

class CommandBase(object):
    
    def __init__(self):
        self.parse()
        self._callAndHandleErrorsForCommands(self.doWork.__name__)

    def _callAndHandleErrorsForCommands(self, methodName, *args, **kw):
        if hasattr(self, 'config'):
            self.debugLevel = self.config.get('debug_level', 3)
        else:
            self.debugLevel = 3
        
        res = 0
        try:
            res = self.__class__.__dict__[methodName](self, *args, **kw)
        except ValueError, ex:
            sys.stderr.writelines('\nError: %s\n' % str(ex))
            sys.exit(3)
        except KeyboardInterrupt, ex:
            self.raiseOrDisplayError(ex)
        except SystemExit, ex:
            self.raiseOrDisplayError(ex)
        except Exception, ex:
            self.raiseOrDisplayError(ex)
        return res
    
    def parse(self):
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
            