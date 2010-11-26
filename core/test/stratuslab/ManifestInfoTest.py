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
import unittest

import stratuslab.Util as Util

from stratuslab.ManifestInfo import ManifestInfo

class AppRepoInfoTest(unittest.TestCase):

    manifest = '''<manifest>
  <created>2010-10-22 11:09:00</created>
  <type>base</type>
  <version>1.0</version>
  <arch>i486</arch>
  <user>Charles LOOMIS</user>
  <os>ttylinux</os>
  <osversion>9.5</osversion>
  <compression>gz</compression>
  <filename>ttylinux-9.5-i486-base-1.0.img.gz</filename>
  <checksum type="md5">d231b143be66fe065c2b8c665f25d7fd</checksum>
  <checksum type="sha1">fbe6fe809f6d81f1f7a5a7f2ac31b925b92372dd</checksum>
  <comments>
Uses standard StratusLab contextualization.
Image only has 'root' account configured.
Only logins via ssh keys are allowed.
</comments>
</manifest>'''

    def testGetInfo(self):        
        info = ManifestInfo()
        info.parseManifest(AppRepoInfoTest.manifest)
        
        self.assertEquals('2010-10-22 11:09:00', info.created)
        
    def testUpdateManifest(self):
        
        ManifestInfo.template = '../../share/template/manifest.xml.tpl'
        
        info = ManifestInfo()
        info.parseManifest(AppRepoInfoTest.manifest)

        self.assertEquals('base', info.type)
        info.type = 'roof'

        xml = info.tostring()
        info = ManifestInfo()
        info.parseManifest(xml)
        
        self.assertEquals('roof', info.type)


if __name__ == "__main__":
    unittest.main()
