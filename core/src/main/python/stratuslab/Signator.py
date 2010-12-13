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
import os

import Util
from Configurable import Configurable
from Exceptions import ConfigurationException


class Signator(Configurable):
    
    def __init__(self, metadataFile, configHolder):
        super(Signator, self).__init__(configHolder)
        self.metadataFile = metadataFile
        if 'outputMetadataFile' not in self.__dict__ or not self.outputMetadataFile:
            self.outputMetadataFile = self.metadataFile + '.sign'

    def sign(self):
        jarLocation = self._findJar()
        javaMainArgs = ' ' + self.metadataFile + ' ' + self.outputMetadataFile + \
                       ' ' + self.p12Cert + ' ' + self.p12Password
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.metadata.GenXmlSign'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '))

    def _findJar(self):
        devLocation = os.path.join(self._moduleDirname(),'../../../../..','sign_validate/target/sign-validate-0.0.1-SNAPSHOT.jar')
        if os.path.exists(devLocation):
            return devLocation

        devLocation = os.path.join('../../../../..','sign_validate/target/sign-validate-0.0.1.jar')
        if os.path.exists(devLocation):
            return devLocation

        sysLocation = os .path.join('/var/lib/stratuslab/java', 'sign-validate-0.0.1.jar')
        if os.path.exists(sysLocation):
            return sysLocation

        raise ConfigurationException('Failed to find sign-validate jar file')

    def _moduleDirname(self):
        return os.path.dirname(__file__)
        
    def validate(self):
        jarLocation = self._findJar()
        javaMainArgs = ' ' + self.metadataFile + \
                       ' ' + self.p12Cert + ' ' + self.p12Password
        cmd = os.path.join('java -cp %s %s' % (jarLocation, 'eu.stratuslab.metadata.ValidateSign'))
        cmd += javaMainArgs
        self._printCalling(cmd)
        return Util.execute(cmd.split(' '))

    def _printCalling(self, cmd):
        self.printDetail('Calling: %s' % cmd)
