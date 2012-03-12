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

from stratuslab.system.BaseSystem import BaseSystem
from stratuslab.system.PackageInfo import PackageInfo

class BaseSystemTest(unittest.TestCase):
    def test_getPackageWithVersionForInstall(self):
        bs = BaseSystem()

        bs.packages['foo'] = PackageInfo('foo')
        assert 'foo' == bs.getPackageWithVersionForInstall('foo')

        bs.packages['foo'] = PackageInfo('foo', packageVersion='1')

        bs.os = 'fedora'
        assert 'foo-1*' == bs.getPackageWithVersionForInstall('foo')

        bs.os = 'ubuntu'
        assert 'foo=1*' == bs.getPackageWithVersionForInstall('foo')

        bs.packages['foo'] = PackageInfo('foo', packageVersion='1*')
        assert 'foo=1**' == bs.getPackageWithVersionForInstall('foo')
