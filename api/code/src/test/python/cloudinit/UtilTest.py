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
                                    for _ in range(2*Util.MAX_BYTES))
        with closing(StringIO()) as buf:
            with closing(GzipFile('', 'wb', 9, buf)) as f:
                f.write(self.TOO_LONG_RAW)
            self.TOO_LONG_GZIP = base64.b64encode(buf.getvalue())

    def tearDown(self):
        pass

    def test_encode_decode_multipart(self):
        initial_text = 'some dummy data to check encoding and decoding'
        encoded = Util.encode_multipart(initial_text)
        decoded = Util.decode_multipart(encoded)

        self.assertTrue(len(encoded) > 0)
        self.assertTrue(len(decoded) > 0)
        self.assertEqual(initial_text, decoded)

    def test_encode_decode_multipart_as_json(self):
        initial_text = 'some dummy data to check encoding and decoding'
        dsmode = 'local'
        encoded = Util.encode_multipart(initial_text)
        decoded = Util.decode_multipart_as_json(dsmode, encoded)

        json_data = json.loads(decoded)

        self.assertTrue(len(encoded) > 0)
        self.assertTrue(len(decoded) > 0)
        self.assertEqual(initial_text, json_data['user-data'])
        self.assertEqual(dsmode, json_data['dsmode'])

    def test_encode_oversized_multipart(self):
        self.assertRaises(ValueError, Util.encode_multipart, self.TOO_LONG_RAW)

    def test_decode_oversized_multipart(self):
        self.assertRaises(ValueError, Util.decode_multipart, self.TOO_LONG_GZIP)

    def test_create_authorized_keys_from_files(self):
        files = []
        values = []
        for i in range(3):
            _, filename = tempfile.mkstemp()
            files.append(filename)
            with open(filename, 'wb') as f:
                value = "value-%d" % i
                f.write(value)
                values.append(value)

        result = Util.create_authorized_keys_from_files(files)

        for f in files:
            os.remove(f)

        self.assertEqual("\n".join(values)+"\n", result)

    def test_create_multipart_string(self):
        files = []
        values = []
        for i in range(3):
            value = "value-%d" % i
            values.append(value)
            files.append(('plain', value))

        result = Util.create_multipart_string(files)

        with closing(StringIO(result)) as buf:
            parser = Parser()
            msg = parser.parse(buf)

        for part in msg.walk():
            if msg.is_multipart():
                i = 0
                for msg in part.get_payload():
                    self.assertEqual(values[i], msg.get_payload())
                    i += 1

    def test_create_multipart_string_with_none(self):
        files = []
        values = []
        for i in range(3):
            value = "value-%d" % i
            values.append(value)
            files.append(('none', value))

        result = Util.create_multipart_string(files)

        self.assertEqual(values[0], result)

    def test_create_multipart_string_from_files(self):
        files = []
        values = []
        for i in range(3):
            _, filename = tempfile.mkstemp()
            files.append(('plain', filename))
            with open(filename, 'wb') as f:
                value = "value-%d" % i
                f.write(value)
                values.append(value)

        result = Util.create_multipart_string_from_files(files)

        for mime, f in files:
            os.remove(f)

        with closing(StringIO(result)) as buf:
            parser = Parser()
            msg = parser.parse(buf)

        for part in msg.walk():
            if msg.is_multipart():
                i = 0
                for msg in part.get_payload():
                    self.assertEqual(values[i], msg.get_payload())
                    i += 1

    def test_create_multipart_string_from_files_with_none(self):
        files = []
        values = []
        for i in range(3):
            _, filename = tempfile.mkstemp()
            files.append(('none', filename))
            with open(filename, 'wb') as f:
                value = "value-%d" % i
                f.write(value)
                values.append(value)

        result = Util.create_multipart_string_from_files(files)

        self.assertEqual(values[0], result)


if __name__ == "__main__":
    unittest.main()
