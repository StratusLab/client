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

import stratuslab.Util as Util
from stratuslab.Compressor import Compressor
import stratuslab.Exceptions as Exceptions
import os

class UtilTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testAppendOrReplaceMultilineBlockInString(self):
        self.assertEqual(Util.appendOrReplaceMultilineBlockInString('', ''), '')
        content = """
line one
line two
#
"""
        data = """
start block
  block LINE ONE
"""
        result = """
line one
line two
#

start block
  block LINE ONE

"""
        self.assertEqual(Util.appendOrReplaceMultilineBlockInString(content, data),
                         result)

        content = """
line one
start block
  block line 1
  block line 2

#
"""
        result = """
line one
start block
  block LINE ONE

#
"""
        self.assertEqual(Util.appendOrReplaceMultilineBlockInString(content, data),
                         result)

        content = """
line one
start block
  block line 1
  block line 2
"""
        result = """
line one
start block
  block LINE ONE

"""
        self.assertEqual(Util.appendOrReplaceMultilineBlockInString(content, data),
                         result)

    def testAppendOrReplaceMultilineBlockInString_StartUntil(self):
        content = """
olcDatabase: {0}config
olcAccess: {0}to *  by dn.base="gidNumber=0+uidNumber=0,cn=peercred,cn=externa
 l,cn=auth" manage  by * none
olcAddContentAcl: TRUE
olcLastMod: TRUE
"""
        data = "olcAccess: ONE LINE"
        start = "olcAccess: {0}to *  by dn.base="
        result = """
olcDatabase: {0}config
%s
olcAddContentAcl: TRUE
olcLastMod: TRUE
""" % data

        self.assertEqual(Util.appendOrReplaceMultilineBlockInString(content, data, start=start, until='olcAdd'),
                         result)

        self.assertEqual(Util.appendOrReplaceMultilineBlockInString(content, data, start='ABC', until='olcAdd'),
                         content+'\n'+data+'\n\n')

    def testExecuteWithOutput(self):
        output = Util.execute('ls -l'.split(), withOutput=True)

        self.assertEquals(type(output), tuple)
        self.assertEquals(len(output), 2)
        self.assertTrue(isinstance(output[1], basestring))
        assert len(output[1]) >= 1

    def testGatewayIpFromNetAddress(self):
        self.assertEquals(Util.gatewayIpFromNetAddress('0.0.0.0'), '0.0.0.1')


    def testConstructEndPoint(self):
        self.assertEquals(Util.constructEndPoint('protocol://address:1234/path'), 'protocol://address:1234/path')
        self.assertEquals(Util.constructEndPoint('address', 'protocol', '1234', 'path'), 'protocol://address:1234/path')

    def testSshCmdRetry(self):
        wrongPort = '33'
        input = 'true', 'localhost', '', wrongPort, 'noname'

        devNull = file('/dev/null','w')
        assert Util.SSH_EXIT_STATUS_ERROR == Util.sshCmd(*input, stderr=devNull)
        devNull.close()

        output = Util.sshCmdWithOutput(*input)
        assert Util.SSH_EXIT_STATUS_ERROR == output[0]
        assert output[1].startswith('ssh: connect to host localhost port 33: Connection refused')

    def testFileGetExtension(self):
        assert Util.fileGetExtension('file.') == ''
        assert Util.fileGetExtension('file') == ''
        assert Util.fileGetExtension('file.txt') == 'txt'
        assert Util.fileGetExtension('file.other.txt') == 'txt'

    def testCheckUrlExists(self):
        self.assertRaises(ValueError, Util.checkUrlExists, (''))
        self.assertRaises(Exceptions.ValidationException, Util.checkUrlExists,
                          ('file:///nosuchfile.txt'))
        self.assertRaises(Exceptions.ValidationException, Util.checkUrlExists,
                          ('http://www.google.com/nosuchfile.txt'))

    def testSanitizeEndpoint(self):
        self.assertEquals(Util.sanitizeEndpoint(''), '')
        self.assertEquals(Util.sanitizeEndpoint('http://localhost', 'https', 888), 'http://localhost')
        self.assertEquals(Util.sanitizeEndpoint('localhost', 'https', 888), 'https://localhost:888')
        self.assertEquals(Util.sanitizeEndpoint('http://localhost:555'), 'http://localhost:555')
        self.assertEquals(Util.sanitizeEndpoint('localhost'), 'https://localhost:80')

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
                self.assertEquals(Util.checksum_file(filename, ['sha1'])[0], foo_size)
                self.assertEquals(Util.checksum_file(filename, ['sha1'])[1],
                                  {'sha1' : '0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33'})

                size, sums = Util.checksum_file(filename, ['md5', 'sha1'])
                self.assertEquals(size, foo_size)
                for sum, val in sums.items():
                    self.assertEquals(checksums_ref[sum], val)

                self.failUnlessRaises(Exception, Util.checksum_file, filename, ['bar'])

            finally:
                os.unlink(filename)
            
    def testfilePutGetContentUnicode(self):
        _, filename = tempfile.mkstemp()
        try:
            Util.filePutContent(filename, unicode('Élément', encoding='utf8'))
            assert 'Élément' == Util.fileGetContent(filename)
        finally:
            os.unlink(filename)

    def testfilePutGetContentStr(self):
        _, filename = tempfile.mkstemp()
        try:
            Util.filePutContent(filename, str('Element'))
            assert 'Element' == Util.fileGetContent(filename)
        finally:
            os.unlink(filename)

    def testgetValueInKB(self):
        self.failUnlessEqual('1', Util.getValueInKB('1'))
        self.failUnlessEqual('123', Util.getValueInKB('123'))
        self.failUnlessEqual('1024', Util.getValueInKB('1MB'))
        self.failUnlessEqual('125952', Util.getValueInKB('123MB'))
        self.failUnlessEqual('1048576', Util.getValueInKB('1GB'))
        self.failUnlessEqual('128974848', Util.getValueInKB('123GB'))

if __name__ == "__main__":
    unittest.main()
