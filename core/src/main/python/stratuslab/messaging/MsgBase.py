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

class MsgBase(object):
    "Interface for all messaging classes."
    
    def __init__(self, configHolder):
        self.msg_endpoint = ''
        self.msg_queue = ''
        self.username = ''
        self.password = ''
        self.verboseLevel = '0'
        configHolder.assign(self)

    def connect(self):
        pass

    def send(self, message):
        "message - string"
        raise NotImplementedError()

    def disconnect(self):
        pass

    def deliver(self, message):
        self.connect()
        self.send(message)
        self.disconnect()
