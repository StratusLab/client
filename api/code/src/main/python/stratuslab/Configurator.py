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
import os
import shutil
from Configurable import Configurable
from Exceptions import ConfigurationException


class Configurator(Configurable):
    def __init__(self, configHolder):
        self.section = None
        super(Configurator, self).__init__(configHolder)

        self.baseConfigFile = self.configFile + '.ref'
        self.config = None
        self.baseConfig = None
        self._load()

    def _load(self):
        self.printDetail('Loading configuration file %s' % self.baseConfigFile)
        self.baseConfig = self.parseConfig(self.baseConfigFile)
        self._createConfigIfRequired()
        self.printDetail('Loading configuration file %s' % self.configFile)
        self.config = self.parseConfig(self.configFile)

    def _createConfigIfRequired(self):
        if not os.path.isfile(self.configFile):
            self.printDetail('Creating user configuration file %s' % self.configFile)
            shutil.copy(self.baseConfigFile, self.configFile)

    def getValue(self, key):
        section, _ = self._findSectionAndValue(key, self.config)
        return self.config.get(section, key)

    def formatDefaultKeys(self):
        columnSize = 25
        defaultConfig = self.convertToSectionDict(self.parseConfig(self.baseConfigFile))

        width = columnSize * 3 + 1
        line = '-' * width
        doubleLine = '=' * width
        startEmphasis = '\033[1;31m'
        stopEmphasis = '\033[0m'

        fields = {'line': line,
                  'doubleLine': doubleLine,
                  'startEmphasis': startEmphasis,
                  'stopEmphasis': stopEmphasis,
                  'section': 'Section'.center(width),
                  'first': 'Config key'.ljust(columnSize),
                  'second': 'Current value'.ljust(columnSize),
                  'third': 'Default value'}

        header = """
%(doubleLine)s
%(startEmphasis)s%(section)s%(stopEmphasis)s
%(line)s

 %(startEmphasis)s%(first)s%(stopEmphasis)s|  %(startEmphasis)s%(second)s%(stopEmphasis)s|  %(startEmphasis)s%(third)s%(stopEmphasis)s

"""

        result = header % fields

        sections = defaultConfig.keys()
        if self.section:
            sections = [self.section]

        first = True
        for section in sections:
            if first:
                result += "%(doubleLine)s\n" % fields
                first = False
            else:
                result += "%(line)s\n" % fields

            result += '%s%s%s'.center(width) % (startEmphasis, section, stopEmphasis)
            result += "\n%(line)s\n" % fields

            keys = defaultConfig[section].keys()
            if keys:
                for key in sorted(keys):
                    result += ' %s|  %s|  %s\n' % (key.ljust(columnSize),
                                                   self.getValue(key).ljust(columnSize),
                                                   defaultConfig[section].get(key))

        return result

    def _convertToDict(self, config):
        dict = {}
        for section in config.sections():
            for k, v in config.items(section):
                dict[k] = v
        return dict

    def setOption(self, key, value):
        section, _ = self._findSectionAndValue(key, self.config)
        self.config.set(section, key, value)
        self.writeUserConfig()

    def _findSectionAndValue(self, key, config):
        section = None
        value = None
        for s in config.sections():
            for k, v in config.items(s):
                if k == key:
                    section = s
                    value = v
                    break
            if section:
                break
        if not section:
            raise ConfigurationException('Key %s does not exist' % key)
        return section, value

    def writeUserConfig(self):
        fd = open(self.configFile, 'wb')
        self.config.write(fd)
        fd.close()

    def revertConfig(self):
        if os.path.isfile(self.userConfigFile):
            os.remove(self.userConfigFile)


class SimpleConfigParser(object):
    FILENAME = 'Unknown'

    def __init__(self):
        self.items = {}

    def load(self, file=None):

        if not file:
            file = open(SimpleConfigParser.FILENAME)

        lines = file.read().split('\n')
        lines = filter(None, lines)
        lines = filter(lambda x: not x.strip().startswith('#'), lines)
        for line in lines:
            parts = line.split('=')
            if len(parts) <= 1:
                raise ValueError('Invalid configuration file format')
            username = parts[0]
            self.items[username] = self.parse_value(parts[1])

    def parse_value(self, value):
        return value

    def get(self, username):
        return self.items[username]
