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
from stratuslab.Uploader import Uploader
from stratuslab.ManifestInfo import ManifestInfo

class ConfigHolderTest(unittest.TestCase):

    def testBuildRepoNameStructureFileUninitializedManifestInfo(self):
        fileNameRef = '----.img.'
        appRepoFileName = '#os#-#osversion#-#arch#-#type#-#version#.img.#compression#'

        info = ManifestInfo()

        fileName = Uploader.buildRepoNameStructure(appRepoFileName, info)

        self.assertEquals(fileNameRef, fileName)

    def testBuildRepoNameStructureFile(self):
        keys = ('os', 'osversion', 'arch', 'type', 'version', 'compression')
        attrsDict = dict(zip(keys, keys))

        fileNameRef = '%(os)s-%(osversion)s-%(arch)s-%(type)s-%(version)s.img.%(compression)s' % attrsDict
        appRepoFileName = '#os#-#osversion#-#arch#-#type#-#version#.img.#compression#'

        info = ManifestInfo()
        info.__dict__.update(attrsDict)

        fileName = Uploader.buildRepoNameStructure(appRepoFileName, info)

        self.assertEquals(fileNameRef, fileName)

    def testBuildRepoNameStructureDirUninitializedManifestInfo(self):
        fileNameRef = 'images//---/'
        appRepoStructure = 'images/#type_#/#os#-#osversion#-#arch#-#type#/#version#'

        info = ManifestInfo()

        fileName = Uploader.buildRepoNameStructure(appRepoStructure, info)

        self.assertEquals(fileNameRef, fileName)

    def testBuildRepoNameStructureDir(self):
        keys = ('os', 'osversion', 'arch', 'type', 'version', 'compression')
        attrsDict = dict(zip(keys, keys))

        fileNameRef = 'images/%(type)s/%(os)s-%(osversion)s-%(arch)s-%(type)s/%(version)s' % attrsDict
        appRepoStructure = 'images/#type_#/#os#-#osversion#-#arch#-#type#/#version#'

        info = ManifestInfo()
        info.__dict__.update(attrsDict)

        fileName = Uploader.buildRepoNameStructure(appRepoStructure, info)

        self.assertEquals(fileNameRef, fileName)

if __name__ == "__main__":
    unittest.main()
