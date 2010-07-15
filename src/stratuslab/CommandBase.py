import sys

class CommandBase(object):
    
    def __init__(self):
        self.parse()
        self._callAndHandleErrorsForCommands(self.doWork.__name__)

    def _callAndHandleErrorsForCommands(self, methodName, *args, **kw):
        res = 0
        try:
            res = self.__class__.__dict__[methodName](self, *args, **kw)
        except ValueError, ex:
            sys.stderr.writelines('\nError: %s\n' % str(ex))
            sys.exit(3)
        except KeyboardInterrupt, ex:
            raise
        except SystemExit, ex:
            raise
        except Exception, ex:
            raise
        return res
    
    def parse(self):
        pass

    def usageExitTooFewArguments(self):
        return self.parser.error('Too few arguments')

    def usageExitTooManyArguments(self):
        return self.parser.error('Too many arguments')

    def usageExitWrongNumberOfArguments(self):
        return self.parser.error('Wrong number of arguments')

