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
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Exceptions import ExecutionException
from stratuslab.Signator import Signator

class ManifestValidator(object):

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder

    def verifySignature(self, imageFilename, metadataFilename):
        signator = Signator(metadataFilename, self.configHolder)
        res = signator.validate()
        if res:
            raise ExecutionException('Failed to validate metadata file')

