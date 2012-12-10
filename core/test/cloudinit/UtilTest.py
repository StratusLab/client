#
# Copyright (c) 2012, Centre National de la Recherche Scientifique (CNRS)
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
import base64
import json
import os
import random
import string
import tempfile
import unittest

from email.Parser import Parser
from contextlib import closing
from gzip import GzipFile
from StringIO import StringIO

import stratuslab.cloudinit.Util as Util

class UtilTest(unittest.TestCase):

    TOO_LONG_RAW = None
    TOO_LONG_GZIP = None

    def setUp(self):
        self.TOO_LONG_RAW = ''.join(random.choice(string.ascii_uppercase)
                                    for x in range(2*Util.MAX_BYTES))
        with closing(StringIO()) as buffer:
            with closing(GzipFile('', 'wb', 9, buffer)) as f:
                f.write(self.TOO_LONG_RAW)
            self.TOO_LONG_GZIP = base64.b64encode(buffer.getvalue())

    def tearDown(self):
        pass

    def testEncodeDecodeMultipart(self):
        initial_text = 'some dummy data to check encoding and decoding'
        encoded = Util.encodeMultipart(initial_text)
        decoded = Util.decodeMultipart(encoded)

        self.assertTrue(len(encoded) > 0)
        self.assertTrue(len(decoded) > 0)
        self.assertEquals(initial_text, decoded)

    def testEncodeDecodeMultipartAsJson(self):
        initial_text = 'some dummy data to check encoding and decoding'
        dsmode = 'local'
        encoded = Util.encodeMultipart(initial_text)
        decoded = Util.decodeMultipartAsJson(dsmode, encoded)

        json_data = json.loads(decoded)

        self.assertTrue(len(encoded) > 0)
        self.assertTrue(len(decoded) > 0)
        self.assertEquals(initial_text, json_data['user-data'])
        self.assertEquals(dsmode, json_data['dsmode'])

    def testEncodeOversizedMultipart(self):
        self.assertRaises(ValueError, Util.encodeMultipart, self.TOO_LONG_RAW)

    def testDecodeOversizedMultipart(self):
        self.assertRaises(ValueError, Util.decodeMultipart, self.TOO_LONG_GZIP)

    def testCreateAuthorizedKeysFromFiles(self):
        files = []
        values = []
        for i in range(3):
            _, filename = tempfile.mkstemp()
            files.append(filename)
            with open(filename, 'wb') as f:
                value = "value-%d" % i
                f.write(value)
                values.append(value)

        result = Util.createAuthorizedKeysFromFiles(files)

        for file in files:
            os.remove(file)

        self.assertEquals("\n".join(values)+"\n", result)

    def testCreateMultipartString(self):
        files = []
        values = []
        for i in range(3):
            value = "value-%d" % i
            values.append(value)
            files.append(('plain', value))

        result = Util.createMultipartString(files)
        print result

        with closing(StringIO(result)) as buffer:
            parser = Parser()
            msg = parser.parse(buffer)

        for part in msg.walk():
            if msg.is_multipart():
                i = 0
                for msg in part.get_payload():
                    self.assertEquals(values[i], msg.get_payload())
                    i = i + 1

    def testCreateMultipartStringFromFiles(self):
        files = []
        values = []
        for i in range(3):
            _, filename = tempfile.mkstemp()
            files.append(('plain', filename))
            with open(filename, 'wb') as f:
                value = "value-%d" % i
                f.write(value)
                values.append(value)

        result = Util.createMultipartStringFromFiles(files)
        print result

        for mime, file in files:
            os.remove(file)

        with closing(StringIO(result)) as buffer:
            parser = Parser()
            msg = parser.parse(buffer)

        for part in msg.walk():
            if msg.is_multipart():
                i = 0
                for msg in part.get_payload():
                    self.assertEquals(values[i], msg.get_payload())
                    i = i + 1


if __name__ == "__main__":
    unittest.main()
