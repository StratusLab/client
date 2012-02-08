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

class InputException(Exception):
    pass

class NetworkException(Exception):
    pass

class ConfigurationException(Exception):
    pass

class OneException(Exception):
    pass

class ValidationException(Exception):
    pass

class ExecutionException(Exception):
    pass

class ServerException(Exception):
    def __init__(self, reason, status=''):
        super(ServerException, self).__init__(reason)
        self.reason = reason
        self.status = status

class ClientException(ServerException):
    def __init__(self, reason, content='', status=''):
        super(ClientException, self).__init__(reason, status=status)
        self.content = content
