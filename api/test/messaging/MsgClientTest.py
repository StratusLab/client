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

import tempfile
import shutil
import unittest

from stratuslab.messaging.MsgClientFactory import getMsgClient
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.messaging.Defaults import MSG_CLIENTS

class MsgClientTest(unittest.TestCase):
    def setUp(self):
        self.ch = ConfigHolder()
        self.temp_dir = tempfile.mkdtemp()
        self.ch.set('msg_queue', self.temp_dir)
        self.ch.set('msg_endpoint', 'foo:1234')

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def testGetMsgClient(self):
        for msg_type in MSG_CLIENTS.keys():
            self.ch.set('msg_type', msg_type)
            getMsgClient(self.ch)

    def testSendImplemented(self):
        for msg_type in MSG_CLIENTS.keys():
            self.ch.set('msg_type', msg_type)
            client = getMsgClient(self.ch)
            try:
                client.send("message")
            except NotImplementedError:
                self.fail("send() should be implemented on '%s'." % msg_type)
            except Exception:
                pass
