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
from stratuslab.Util import printWarning

class Installator(object):
    ''' Base interface for installator '''
    
    def __init__(self):
        self.nodeAddr = None
    
    def install(self):
        if self.nodeAddr:
            self._installNode()
        else:
            self._installFrontend()
    
    def _installNode(self):
        printWarning('Nothing to install on node for %s' % self.__class__.__name__)
        
    def _installFrontend(self):
        printWarning('Nothing to install on frontend for %s' % self.__class__.__name__)
    
    def setup(self):
        if self.nodeAddr:
            self._setupNode()
        else:
            self._setupFrontend()
    
    def _setupNode(self):
        printWarning('Nothing to setup on node for %s' % self.__class__.__name__)
        
    def _setupFrontend(self):
        printWarning('Nothing to setup on frontend for %s' % self.__class__.__name__)
    
    def startServices(self):
        if self.nodeAddr:
            self._startServicesNode()
        else:
            self._startServicesFrontend()
            
    def _startServicesNode(self):
        printWarning('No service to start on node for %s' % self.__class__.__name__)
        
    def _startServicesFrontend(self):
        printWarning('No service to start on node for %s' % self.__class__.__name__)
    