#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, SixSq Sarl
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

import unittest

from mock.mock import Mock
from stratuslab.installator.BaseInstallator import BaseInstallator
import stratuslab.ConfigHolder as ConfigHolder

class BaseInstallatorTest(unittest.TestCase):

    def setUp(self):
        self.ch = ConfigHolder.ConfigHolder()

    def tearDown(self):
        reload(ConfigHolder)

    def _initBaseInstallator(self, install=False):
        baseInst = BaseInstallator()
        
        self.ch = self._initConfigHolder(install)
        baseInst._assignConfigHolder(self.ch)

        return baseInst

    def _initConfigHolder(self, install=False):
        ch = ConfigHolder.ConfigHolder()
        ch.verboseLevel = 0
        for name in BaseInstallator.availableInstallatorNames():
            ch.set('install%s' % name.title(), install)

        return ch

    def test_selectCompenenstToInstall_All(self):
        baseInst = self._initBaseInstallator(install=True)

        components = baseInst._selectCompenentsToInstall()
        self.assertEquals(components, baseInst.availableInstallatorNames())

    def test_selectCompenenstToInstall_Custom(self):
        baseInst = self._initBaseInstallator()

        self.ch.set('installOpenldap', True)
        self.ch.set('installPort-Translation', True)
        baseInst._assignConfigHolder(self.ch)

        components = baseInst._selectCompenentsToInstall()
        self.assertEquals(components, ('openldap', 'port-translation'))

    def test_launchInstallator_CheckCallOrder(self):
        BaseInstallator._executeInstall = Mock()

        COMPONENTS_NUMBER = 2
        COMPONENTS = BaseInstallator.availableInstallatorNames()[:COMPONENTS_NUMBER]
        
        baseInst = self._initBaseInstallator()
        baseInst._launchInstallator(COMPONENTS)

        assert baseInst._executeInstall.call_count == COMPONENTS_NUMBER

        componetsToInstall = []
        for call_args in baseInst._executeInstall.call_args_list:
            args, _ = call_args
            componentName = args[0]
            componetsToInstall.append(componentName)
        assert COMPONENTS == tuple(componetsToInstall)

    def test_selectCompenenstToInstall_ConfFile(self):
        baseInst = self._initBaseInstallator()

        self.ch.config['openldap'] = '1'
        self.ch.config['port_translation'] = 'yes'
        self.ch.config['opennebula'] = 'no'
        baseInst._assignConfigHolder(self.ch)

        components = baseInst._selectCompenentsToInstall()
        self.assertEquals(components, ('openldap', 'port-translation'))
        

if __name__ == "__main__":
    unittest.main()
