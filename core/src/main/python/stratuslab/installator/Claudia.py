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
import stratuslab.system.SystemFactory as SystemFactory

class Claudia(object):

    def __init__(self, configHolder):
        # this call makes all configuration parameters and command-line options
        # available as fields of self using the Camel case convention.
        # For example, the config parameter 'one_username' is available as self.oneUsername.
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        # add your packages here 
        #self.packages = ['apache2']
        self.packages = []

    def _overrideValueInFile(self, key, value, fileName):
        # Here's how you could override config files...
        search = key + ' = '
        replace = key + ' = ' + value
        Util.appendOrReplaceInFile(fileName, search, replace)

    def run(self):
        self._installPackages()
        self._configure()
        self._startServices()
        
    def _installPackages(self):
        if self.packages:
            self.system.installPackages(self.packages)

    def _configure(self):
        pass

    def _startServices(self):
        self.system.execute(['ls', '-l'])
        self.system.execute(['pwd'])
