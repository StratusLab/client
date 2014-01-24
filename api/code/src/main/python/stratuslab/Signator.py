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

import stratuslab.Util as Util
from Configurable import Configurable
from Exceptions import ConfigurationException

class Signator(Configurable):

    @staticmethod
    def findJar():
        dirs = []
        module_dirname = os.path.dirname(__file__)
        devRelativePath = '../../../../../../stratuslab-marketplace/metadata/target'
        dirs.append(os.path.join(module_dirname, devRelativePath))
        tarballRelativePath = '../../../../java/'
        dirs.append(os.path.join(module_dirname, tarballRelativePath))
        easyInstallRelativePath = '../java/'
        dirs.append(os.path.join(module_dirname, easyInstallRelativePath))
        dirs.append('/var/lib/stratuslab/java')
        
        for dir in dirs:
            try:
                jarFile = Util.fileFind(dir, 'metadata', 'dependencies.jar')
                return jarFile
            except ValueError:
                pass

    def __init__(self, manifestFile, configHolder):
        self.outputManifestFile = None
        self.renamedInputManifestFile = manifestFile
        self.email = ''
        super(Signator, self).__init__(configHolder)
        self.manifestFile = manifestFile
        if not self.outputManifestFile:
            self.outputManifestFile = self.manifestFile
            self.renamedInputManifestFile = self.manifestFile + '.orig'
        self.tempManifestFile = self.manifestFile + '.new'

    def sign(self):
        res, output = self._sign()
        if res:
            Util.printError(output, exit=False)
            self._cleanupTempFile()
        else:
            self._renameFiles()
        return res

    def _sign(self):
        jarLocation = self._findJar()
        self.printDetail('Signature jar file: %s' % jarLocation)
        javaMainArgs = ' ' + self.manifestFile + ' ' + self.tempManifestFile + \
                       ' ' + self.p12Certificate + ' ' + self.p12Password + \
                       ' ' + self.email
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.marketplace.metadata.SignMetadata'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '),withOutput=True)

    def _findJar(self):
        jarLocation = self.findJar()
        if not jarLocation:
            raise ConfigurationException('Failed to find metadata jar file')
        return jarLocation

    def _renameFiles(self):
        self.printDetail('Renaming input file from %s to %s' % (self.manifestFile, self.renamedInputManifestFile), verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
        os.rename(self.manifestFile, self.renamedInputManifestFile)
        self.printDetail('Renaming output file from %s to %s' % (self.tempManifestFile, self.outputManifestFile), verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
        os.rename(self.tempManifestFile, self.outputManifestFile)

    def _cleanupTempFile(self):
        if os.path.isfile(self.tempManifestFile):
            os.remove(self.tempManifestFile)

    def validate(self):
        jarLocation = self._findJar()
        javaMainArgs = ' ' + self.manifestFile
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.marketplace.metadata.CheckMetadata'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '))

    def _printCalling(self, cmd):
        Util.printDetail('Calling: %s' % cmd, verboseLevel=self.verboseLevel,
                         verboseThreshold=Util.VERBOSE_LEVEL_DETAILED)
