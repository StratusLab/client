# encoding: utf8

import os
import shutil
import unittest

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.messaging.DirectoryQueue import DirectoryQueue

class DirectoryQueueTest(unittest.TestCase):

    def setUp(self):
        self.test_queue = os.getcwd()+'/test_queue'

    def tearDown(self):
        shutil.rmtree(self.test_queue, ignore_errors=True)
    
    def test_send(self):
        dirq = DirectoryQueue(ConfigHolder({'msg_queue':self.test_queue}))
        try:
            dirq.send(u'{"foo":"Élément"}')
        except Exception, e:
            self.fail('Failed with %s' % str(e))
