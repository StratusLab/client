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
import os
import unittest

from mock.mock import Mock

from stratuslab.Runner import Runner
import stratuslab.ConfigHolder as ConfigHolder
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader

class RunnerTest(unittest.TestCase):
    
    def setUp(self):
        Runner._setCloudContext = Mock()

    def tearDown(self):
        reload(ConfigHolder)

    def testDisksBusTypeVirtio(self):

        runner = self._getRunnerForManifestInFile('manifest-disks-bus-virtio.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('vd', vm_params['vm_disks_prefix'])
        
    def testDisksBusTypeIde(self):
        
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-ide.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_')
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('hd', vm_params['vm_disks_prefix'])

    def testDisksBusTypeExtraDisk(self):
        
        ch = ConfigHolder.ConfigHolder()
        ch.set('extraDiskSize', '1')

        # IDE        
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-ide.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  ch)
        vm_params = runner._vmParamDict()
        extra_disk = Runner.EXTRA_DISK % {'extraDiskSize' : '1',
                                          'vm_disks_prefix' : 'hd'}
        self.failUnlessEqual(extra_disk, vm_params['extra_disk'])

        # VIRTIO        
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-virtio.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  ch)
        vm_params = runner._vmParamDict()
        extra_disk = Runner.EXTRA_DISK % {'extraDiskSize' : '1',
                                          'vm_disks_prefix' : 'vd'}
        self.failUnlessEqual(extra_disk, vm_params['extra_disk'])
        
    def testDisksBusTypeReadonlyDisk(self):
        configHolder = ConfigHolder.ConfigHolder()

        uuid = 'f25cd0dc-e56f-4eea-be0c-88d866a2c73c'
        configHolder.set('readonlyDiskId', uuid)

        # IDE        
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-ide.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  configHolder)
        vm_params = runner._vmParamDict()
        readonly_disk = Runner.READONLY_DISK % {'readonlyDiskId' : uuid,
                                                'vm_disks_prefix' : 'hd'}
        self.failUnlessEqual(readonly_disk, vm_params['readonly_disk'])

        # VIRTIO        
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-virtio.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  configHolder)
        vm_params = runner._vmParamDict()
        readonly_disk = Runner.READONLY_DISK % {'readonlyDiskId' : uuid,
                                                'vm_disks_prefix' : 'vd'}
        self.failUnlessEqual(readonly_disk, vm_params['readonly_disk'])

    def testDisksBusTypeFromCommandLine(self):
        configHolder = ConfigHolder.ConfigHolder()

        # IDE
        configHolder.set('vmDisksBus', 'ide')
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-virtio.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  configHolder)
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('hd', vm_params['vm_disks_prefix'])

        # VIRTIO
        configHolder.set('vmDisksBus', 'virtio')
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-ide.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  configHolder)
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('vd', vm_params['vm_disks_prefix'])
        
        # SCSI
        configHolder.set('vmDisksBus', 'scsi')
        runner = self._getRunnerForManifestInFile('manifest-disks-bus-virtio.xml',
                                                  'MMZu9WvwKIro-rtBQfDk4PsKO7_',
                                                  configHolder)
        vm_params = runner._vmParamDict()
        self.failUnlessEqual('sd', vm_params['vm_disks_prefix'])

    def _getRunnerForManifestInFile(self, filename, imageid, ch=ConfigHolder.ConfigHolder()):
        ch.set('verboseLevel', 0)
    
        self._mockManifestDownloaderToReadFromFile(filename)
        
        runner = Runner(imageid, ch)
        
        return runner

    @staticmethod
    def _mockManifestDownloaderToReadFromFile(filename):
        manifest = open(os.path.join(os.path.dirname(__file__), 'resources',
                                     filename)).read()
        mock = Mock(return_value = ManifestDownloader._parseXml(manifest))
        ManifestDownloader._download = mock
    
if __name__ == "__main__":
    unittest.main()
