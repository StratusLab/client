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

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.messaging.MessagePublishers import ImageIdPublisher
from stratuslab.Exceptions import InputException

class ImageIdPublisherTest(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass

    def testSetImageIdOnMessage(self):
        configHolder = ConfigHolder()
        configHolder.set('msg_type', 'amazonsqs')

        self.failUnlessRaises(InputException, ImageIdPublisher, 
                                                *('', '', configHolder))

        publisher = ImageIdPublisher('', 'Oj3KIhOEZ4LPhJK7LdFdfluTw17', configHolder)
        assert '{"imageid": "Oj3KIhOEZ4LPhJK7LdFdfluTw17"}' == publisher.message

        publisher = ImageIdPublisher('{"foo": "bar"}', 
                                     'Oj3KIhOEZ4LPhJK7LdFdfluTw17', configHolder)
        assert '{"foo": "bar", "imageid": "Oj3KIhOEZ4LPhJK7LdFdfluTw17"}' == publisher.message
