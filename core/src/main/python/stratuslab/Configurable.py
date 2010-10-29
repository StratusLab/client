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
import stratuslab.Util as Util
from stratuslab.Util import printAction
from stratuslab.Util import printStep
from stratuslab.Util import printDetail
from stratuslab.Util import printWarning
from stratuslab.Util import printError
from stratuslab.ConfigHolder import ConfigHolder

class Configurable(object):
    def __init__(self, configHolder):
        configHolder.assign(self)
        self.verify()

    @staticmethod
    def convertToSectionDict(config):
        dicts = {}
        for section in config.sections():
            dict = {}
            for k,v in config.items(section):
                dict[k] = v
            dicts[section] = dict
        return dicts

    def parseConfig(self, configFileName):
        return ConfigHolder.parseConfig(configFileName)

    def verify(self):
        pass

    def printAction(self, msg):
        printAction(msg)

    def printStep(self, msg):
        printStep(msg)
    
    def printDetail(self, msg, verboseThreshold=Util.NORMAL_VERBOSE_LEVEL):
        printDetail(msg, self.verboseLevel, verboseThreshold)

    def printWarning(self, msg):
        printWarning(msg)

    def printError(self, msg):
        printError(msg, exit=False)
