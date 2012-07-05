import tempfile
import shutil
import unittest

from stratuslab.messaging.MsgClientFactory import getMsgClient
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.messaging.Defaults import MSG_CLIENTS

class MsgClientTest(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass
    
    def xtestGetMsgClient(self):
        ch = ConfigHolder()
        temp_dir = tempfile.mkdtemp()
        ch.set('msg_queue', temp_dir)
        ch.set('msg_endpoint', 'foo:1234')
        for msg_type in MSG_CLIENTS.keys():
            ch.set('msg_type', msg_type)
            getMsgClient(ch)

        shutil.rmtree(temp_dir, ignore_errors=True)
