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

from dirq.QueueSimple import QueueSimple
from stratuslab.messaging.MsgBase import MsgBase

class DirectoryQueue(MsgBase):
    def __init__(self, configHolder):
        super(DirectoryQueue, self).__init__(configHolder)

        self.queue = QueueSimple(self.msg_queue)

    def send(self, message):
        self.queue.add(message)
