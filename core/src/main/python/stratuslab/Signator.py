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
        javaMainArgs = ' ' + self.manifestFile + ' ' + self.tempManifestFile + \
                       ' ' + self.p12Certificate + ' ' + self.p12Password + \
                       ' ' + self.email
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.marketplace.metadata.SignMetadata'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '))

    def _findJar(self):
        dirs = []
        devRelativePath = '../../../../../../stratuslab-marketplace/metadata/target'
        dirs.append(os.path.join(self._moduleDirname(), devRelativePath))
        tarballRelativePath = '../../../../java/'
        dirs.append(os.path.join(self._moduleDirname(), tarballRelativePath))
        dirs.append('/var/lib/stratuslab/java')
        
        for dir in dirs:
            try:
                jarFile = self._findFile(dir, 'marketplace-metadata', 'dependencies.jar')
                self.printDetail('Loading signature jar file: %s' % jarFile)
                return jarFile
            except ValueError:
                pass

        raise ConfigurationException('Failed to find metadata jar file')

    def _moduleDirname(self):
        return os.path.dirname(__file__)
        
    def _findFile(self, dir, start='', end=''):
        try:
            for file in os.listdir(dir):
                if file.startswith(start) and file.endswith(end):
                    return os.path.join(dir, file)
        except OSError:
            pass

        raise ValueError("Can't find file starting with %s and ending with %s in directory %s" % (start, end, dir))

    def _renameFiles(self):
        self.printDetail('Renaming input file from %s to %s' % (self.manifestFile, self.renamedInputManifestFile), verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
        os.rename(self.manifestFile, self.renamedInputManifestFile)
        self.printDetail('Renaming output file from %s to %s' % (self.tempManifestFile, self.outputManifestFile), verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
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
        return Util.execute(cmd.split(' '),withOutput=True)

    def _printCalling(self, cmd):
        Util.printDetail('Calling: %s' % cmd, verboseLevel=self.verboseLevel,
                         verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
