#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
import os
from optparse import OptionParser
import xmlrpclib
import json

import stratuslab.Util as Util
from stratuslab.VersionChecker import VersionChecker
import stratuslab.Exceptions as Exceptions
from stratuslab.ConfigHolder import ConfigHolder, UserConfigurator
from stratuslab.Exceptions import ConfigurationException

class CommandBase(object):
    
    def __init__(self):
        self.options = None
        self.config  = {}
        self._configKeysClassAttrsTwoWayMap = {}

        self.verboseLevel = 0
        self.parser = None
        self._setParserAndParse()

        try:
            self, self._loadConfigFileAndUpdateOptions()
        except Exception, ex:
            self.raiseOrDisplayError(str(ex))

        self.checkOptions()
        self._callAndHandleErrors(self, self.doWork.__name__)

    def _setParserAndParse(self):
        self.parser = OptionParser(version="${project.version}")
        self.parser.add_option('-v', '--verbose', dest='verboseLevel',
                help='verbose level. Add more to get more details',
                action='count', default=self.verboseLevel)

        self._addConfigFileOption()

        self.parse()
        self.verboseLevel = self.options.verboseLevel
        
    def _addConfigFileOption(self):
        pass

    def _loadConfigFileAndUpdateOptions(self):
        pass

    def _callAndHandleErrors(self, methodName, *args, **kw):
        
        try:
            Util.runMethodByName(methodName, *args, **kw)
        except ValueError, ex:
            self.raiseOrDisplayError('Error: %s\n' % str(ex))
        except xmlrpclib.ProtocolError, ex:
            self.raiseOrDisplayError('Error: %s' % ex.errmsg)
        except socket.sslerror, ex:
            self._checkPythonVersionAndRaise()
            self.raiseOrDisplayError('Network error: %s' % ex)
        except socket.error, ex:
            self.raiseOrDisplayError('Network error: %s' % ex)
        except socket.gaierror, ex:
            self.raiseOrDisplayError('Network error: %s' % ex)
        except Exceptions.ClientException, ex:
            msg = 'Error: ' + ex.reason
            if ex.content and (self.verboseLevel > 1):
                msg += '\nDetail: ' + ex.content
            if getattr(ex, 'mediaType', None) == 'json':
                error = json.loads(ex.content)
                msg = 'Error: %s (code %d)' % (error['message'], error['code'])
            self.raiseOrDisplayError(msg)
        except Exception, ex:
            self.raiseOrDisplayError('Error: %s' % ex)

    def _checkPythonVersionAndRaise(self):
        try:
            VersionChecker().check()
        except Exceptions.ValidationException, ex:
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
        if self.verboseLevel > 2:
            raise
        else:
            Util.printError(errorMsg, exit=False)
        sys.exit(-1)

    def printDetail(self, message):
        Util.printDetail(message, self)

    def printError(self, message):
        Util.printError(message, self)
        
    def printMandatoryOptionError(self, option):
        self.printError('Missing mandatory %s option' % option)

class CommandBaseUser(CommandBase):
    def __init__(self):
        super(CommandBaseUser, self).__init__()

    def _addConfigFileOption(self):
        ConfigHolder.addConfigFileUserOption(self.parser)

    def _loadConfigFileAndUpdateOptions(self):
        self._loadConfigFile()
        self._updateOptionsFromConfigFile()

    def _loadConfigFile(self):
        if not hasattr(self.options, 'configFile'):
            return

        configFile = self.options.configFile

        if configFile == Util.defaultConfigFileUser:
            if not os.path.exists(configFile):
                Util.printDetail('[WARNING] Default user configuration file does not exist: %s' % 
                                  configFile, verboseLevel=self.verboseLevel)
                return

        selected_section = None
        if hasattr(self.options, 'selected_section'):
            selected_section = self.options.selected_section

        try:
            self.config, self._configKeysClassAttrsTwoWayMap = \
                UserConfigurator.configFileToDictWithFormattedKeys(configFile, withMap=True, selected_section=selected_section)
        except ConfigurationException, ex:
            raise ConfigurationException('Error parsing user configuration file %s' % configFile + '. Details: %s' % ex)

    def _updateOptionsFromConfigFile(self):
        """Order of precedence:
        * command line option
        * environment variable
        * configuration file
        * default value

        Update of the corresponding options object key/value pairs can only be 
        done if neither corresponding command line option nor environment
        variable was given/set.

        The following key/attribute/env.var. naming is assumed:

         configuration file | class attribute | environment variable
         ----------------- + --------------- + --------------------
         p12_certificate   | p12Certificate  | STRATUSLAB_P12_CERTIFICATE
        """

        if not self.config:
            return

        for k in self.config:
            if k in self.options.__dict__:
                valueFromOptions = getattr(self.options, k)
                # Set the value from configuration file: 
                # * if attribute is empty
                if not valueFromOptions:
                    setattr(self.options, k, self.config[k])
                # * if default is equal to "provided" value, we may assume that 
                #   the option wasn't given on command line; but we are going 
                #   to double check this in each Option object of the parser as 
                #   the same value might have been provided via environment var.
                elif valueFromOptions == self.parser.defaults[k]:
                    for optionObj in self.parser.option_list:
                        # work only with Option object for the particular key 
                        if optionObj.dest != k:
                            continue
                        # Update iff
                        # * the long option is NOT in the list of the CLI arguments
                        if not (optionObj._long_opts[0] in sys.argv):
                            # * and not set via corresponding environment variable
                            envVar = 'STRATUSLAB_%s' % self._configKeysClassAttrsTwoWayMap[k].upper()
                            if not os.getenv(envVar):
                                setattr(self.options, k, self.config[k])
                else:
                    pass

class CommandBaseSysadmin(CommandBase):
    def __init__(self):
        super(CommandBaseSysadmin, self).__init__()

    def _addConfigFileOption(self):
        ConfigHolder.addConfigFileSysadminOption(self.parser)
