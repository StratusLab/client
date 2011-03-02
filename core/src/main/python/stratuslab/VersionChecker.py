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

import sys

from Exceptions import ValidationException

class VersionChecker(object):

    MINIMUM_VERSION = (2, 6)

    def _getPythonVersion(self):
        return sys.version_info
    
    def check(self):
        if self._getPythonVersion() < VersionChecker.MINIMUM_VERSION:
            raise ValidationException('python version must be %s or greater' % '.'.join(map(str,VersionChecker.MINIMUM_VERSION)))
