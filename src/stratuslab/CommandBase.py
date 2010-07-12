import sys

class CommandBase(object):
    
    def __init__(self, argv=None):
        self._callAndHandleErrorsForCommands(self.doWork.__name__)

    def _callAndHandleErrorsForCommands(self, methodName, *args, **kw):
        res = 0
        try:
            res = self.__class__.__dict__[methodName](self, *args, **kw)
        except ValueError, ex:
            sys.stderr.writelines('\nError: %s\n' % str(ex))
            sys.exit(3)
        #except NetworkError, ex:
        #    sys.stderr.writelines('\nError: couldn\'t connect to the server. ')
        #    sys.stderr.writelines('Check network connection and server, and try again.')
        #    sys.stderr.writelines('\nError details: %s\n' % ex)
        #    sys.exit(4)
        #except ServerError, ex:
        #    sys.stderr.writelines("\nError: the following unexpected error was detected:\n   '%s'\n" % str(ex))
        #    sys.exit(5)
        #except SecurityError, ex:
        #    sys.stderr.writelines("\nSecurity Error: %s \n" % str(ex))
        #    sys.exit(6)
        #except ClientError, ex:
        #    sys.stderr.writelines("\nError: %s\n" % str(ex))
        #    sys.exit(7)
        except KeyboardInterrupt, ex:
            raise
        #except AbortException, ex:
        #    sys.stderr.writelines('\nError: %s\n' % str(ex))
        #    sys.exit(8)
        #except TimeoutException, ex:
        #    sys.stderr.writelines('\nError: %s\n' % str(ex))
        #    sys.exit(9)
        except SystemExit, ex:
            raise
        except Exception, ex:
            raise
        return res

    def usageExitTooFewArguments(self):
        return self.parser.error('Too few arguments')

    def usageExitTooManyArguments(self):
        return self.parser.error('Too many arguments')

    def usageExitWrongNumberOfArguments(self):
        return self.parser.error('Wrong number of arguments')

