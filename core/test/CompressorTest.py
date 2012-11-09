# -*- coding: utf-8 -*-
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
import tempfile
import unittest

import stratuslab.Exceptions as Exceptions
from stratuslab.Compressor import Compressor
import os

class CompressorTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testGetCompressionFormat(self):
        for suffix in Compressor.compressionFormats:
            fname = "dummy.%s" % suffix
            self.assertEquals(Compressor.getCompressionFormat(fname), suffix)
            fname = "dummy.%s" % suffix.upper()
            self.assertEquals(Compressor.getCompressionFormat(fname), suffix)
        self.assertEquals(Compressor.getCompressionFormat("dummy"), "")
        self.assertEquals(Compressor.getCompressionFormat(""), "")

    def _foo_tempfile(self, suffix=''):
        fd, filename = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        f = Compressor.openCompressedFile(filename, options='wb')
        try:
            f.write('foo')
        finally:
            f.close()

        return filename
            
    def testChecksumFile(self):

        filenames = []
        filenames.append(self._foo_tempfile())
        filenames.append(self._foo_tempfile('.gz'))
        filenames.append(self._foo_tempfile('.bz2'))

        # checksums of 'foo'
        foo_size = 3
        checksums_ref = {'md5' : 'acbd18db4cc2f85cedef654fccc4a4d8',
                         'sha1': '0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33',}

        for filename in filenames:
            try:
                size, sums = Compressor.checksum_file(filename, ['sha1'])
                self.assertEquals(size, foo_size)
                self.assertEquals(sums, {'sha1' : '0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33'})

                size, sums = Compressor.checksum_file(filename, ['md5', 'sha1'])
                self.assertEquals(size, foo_size)
                for sum, val in sums.items():
                    self.assertEquals(checksums_ref[sum], val)

                self.failUnlessRaises(Exception, Compressor.checksum_file, filename, ['bar'])

            finally:
                os.unlink(filename)
            

if __name__ == "__main__":
    unittest.main()
