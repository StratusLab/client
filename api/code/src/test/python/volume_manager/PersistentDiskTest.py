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
import unittest
from datetime import datetime
from datetime import timedelta

from mock.mock import Mock
from stratuslab.Exceptions import ValidationException
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.volume_manager.PersistentDisk import PersistentDisk


class PersistentDiskTest(unittest.TestCase):

    def testCleanQuarantine(self):
        now = datetime.now()
        past = str(now - timedelta(days=1))
        way_past = str(now - timedelta(days=3))

        mock = Mock(return_value = [{'quarantine': past, 'uuid': 'past'},
                                    {'quarantine': way_past, 'uuid': 'way_past'},
                                    {'quarantine': str(now), 'uuid': 'now'}])

        config = ConfigHolder()
        config.set('endpoint', 'something')
        pd = PersistentDisk(config)
        pd.quarantinePeriod = '2d'

        pd.describeVolumes = mock
        pd.deleteVolume = Mock()
        pd._setPDiskUserCredentials = Mock()

        pd.cleanQuarantine()

        self.assertEqual(('way_past',), pd.deleteVolume.call_args[0])

        self.assertEqual(1, pd.deleteVolume.call_count)

    def testParseQuarantinePeriod(self):
        config = ConfigHolder()
        config.set('endpoint', 'something')
        pd = PersistentDisk(config)

        pd.quarantinePeriod = None
        self.assertRaises(ValidationException, pd._getQuarantinePeriod)
        pd.quarantinePeriod = '15x'
        self.assertRaises(ValidationException, pd._getQuarantinePeriod)
        pd.quarantinePeriod = 'xym'
        self.assertRaises(ValidationException, pd._getQuarantinePeriod)

        pd.quarantinePeriod = '15'
        self.assertEqual(pd._getQuarantinePeriod(), 15)
        pd.quarantinePeriod = '15m'
        self.assertEqual(pd._getQuarantinePeriod(), 15)
        pd.quarantinePeriod = '15h'
        self.assertEqual(pd._getQuarantinePeriod(), 15*60)
        pd.quarantinePeriod = '15d'
        self.assertEqual(pd._getQuarantinePeriod(), 15*60*24)

    def testGetMountVmIds(self):
        pd = PersistentDisk()
        pd.endpoint = 'https://example.com:8445/pwd'
        pd._raiseOnErrors = pd._setPDiskUserCredentials =\
                                                pd._initPDiskConnection = Mock()
        pd._getJson = Mock(return_value=('', '[{"vmId":"1234", "device":"static"}]'))
        assert ['1234'] == pd.getMountVmIds('foo')
        pd._getJson.assert_called_once_with(*('https://example.com:8445/pwd/disks/foo/mounts',), **{})

        pd._getJson = Mock(return_value=('', 
                '[{"vmId":"1234", "device":"static"}, {"vmId":"4567", "device":"static"}]'))
        assert ['1234', '4567'] == pd.getMountVmIds('bar')
        pd._getJson.assert_called_with(*('https://example.com:8445/pwd/disks/bar/mounts',), **{})


if __name__ == "__main__":
    unittest.main()
