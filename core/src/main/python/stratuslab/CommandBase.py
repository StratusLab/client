#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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
import socket
import sys
from optparse import OptionParser
import xmlrpclib

import stratuslab.Util as Util
from stratuslab.VersionChecker import VersionChecker
from stratuslab.Exceptions import ValidationException

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
                help='verbose level. Add more to get more details.',
                action='count', default=self.verboseLevel)
        self.parse()
        self.verboseLevel = self.options.verboseLevel
        
    def _callAndHandleErrors(self, methodName, *args, **kw):
        
        try:
            Util.runMethodByName(methodName, *args, **kw)
        except ValueError, ex:
            sys.stderr.writelines('\nError: %s\n' % str(ex))
            sys.exit(3)
        except xmlrpclib.ProtocolError, ex:
            self.raiseOrDisplayError('Error: %s' % ex.errmsg)
        except socket.sslerror, ex:
            self._checkPythonVersionAndRaise()
            self.raiseOrDisplayError('Network error: %s' % ex)
        except socket.error, ex:
            self.raiseOrDisplayError('Network error: %s' % ex)
        except socket.gaierror, ex:
            self.raiseOrDisplayError('Network error: %s' % ex)
        except Exception, ex:
            self.raiseOrDisplayError(ex)

    def _checkPythonVersionAndRaise(self):
        try:
            VersionChecker().check()
        except ValidationException, ex:
            self.raiseOrDisplayError(ex)
        
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
            Util.printError(errorMsg, exit=False)
        sys.exit(-1)

    def printDetail(self, message):
        Util.printDetail(message, self)
