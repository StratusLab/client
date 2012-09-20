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
import stratuslab.Util as Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab import Exceptions

class Configurable(object):
    def __init__(self, configHolder):
        configHolder.assign(self)
        self._verify()

    @staticmethod
    def convertToSectionDict(config):
        dicts = {}
        for section in config.sections():
            _dict = {}
            for k,v in config.items(section):
                _dict[k] = v
            dicts[section] = _dict
        return dicts

    def parseConfig(self, configFileName):
        return ConfigHolder.parseConfig(configFileName)

    def _verify(self):
        attrs = ['verboseLevel']
        for attr in attrs:
            if not hasattr(self, attr):
                raise Exceptions.ValidationException("%s: missing attribute '%s'" % \
                                                     (self.__class__.__name__, attr))
        self.verify()

    def verify(self):
        pass

    def printAction(self, msg):
        Util.printAction(msg)

    def printStep(self, msg):
        Util.printStep(msg)
    
    def printDetail(self, msg, verboseThreshold=Util.VERBOSE_LEVEL_NORMAL):
        Util.printDetail(msg, self.verboseLevel, verboseThreshold)

    def printWarning(self, msg):
        Util.printWarning(msg)

    def printError(self, msg):
        Util.printError(msg, exit=False)
