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

import Util
from Configurable import Configurable
from Exceptions import ConfigurationException


class Signator(Configurable):
    
    def __init__(self, manifestFile, configHolder):
        super(Signator, self).__init__(configHolder)
        self.manifestFile = manifestFile
        if 'outputManifestFile' not in self.__dict__ or not self.outputManifestFile:
            self.outputManifestFile = self.manifestFile + '.sign'

    def sign(self):
        jarLocation = self._findJar()
        javaMainArgs = ' ' + self.manifestFile + ' ' + self.outputManifestFile + \
                       ' ' + self.p12Cert + ' ' + self.p12Password
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.marketplace.metadata.SignMetadata'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '))

    def _findJar(self):
        dirs = []
        tarballRelativePath = '../../../../java/'
        dirs.append(os.path.join(self._moduleDirname(), tarballRelativePath))
        dirs.append('/var/lib/stratuslab/java')
        
        for dir in dirs:
            try:
                return self._findFile(dir, 'metadata', '.jar')
            except:
                pass

        raise ConfigurationException('Failed to find metadata jar file')

    def _findFile(self, dir, start='', end=''):
        for file in os.listdir(dir):
            if file.startswith(start) and file.endswith(end):
                return os.path.join(dir, file)
        raise ValueError("Can't find file starting with %s and ending with %s in directory %s" % (start, end, dir))

    def _moduleDirname(self):
        return os.path.dirname(__file__)
        
    def validate(self):
        jarLocation = self._findJar()
        javaMainArgs = ' ' + self.manifestFile
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.marketplace.metadata.CheckMetadata'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '))

    def _printCalling(self, cmd):
        self.printDetail('Calling: %s' % cmd, verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
