#!/usr/bin/env python
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, Centre National de la Recherche Scientifique (CNRS)
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

import json
from stratuslab.HttpClient import HttpClient

class PersistentDisk(object):
    
    def __init__(self, configHolder):
        self.client = HttpClient(configHolder)
        self.client.useCredentials(True)
        self.config = configHolder
        self.pdiskEndpoint = self._getPdiskEndpoint()
        
    def volumeList(self):
        listVolUrl = '%s/disks/?json' % self.pdiskEndpoint
        _, jsonDiskList = self.client.get(listVolUrl, accept='text/plain')
        return json.loads(jsonDiskList)
        
    def createVolume(self, size, tag):
        createVolumeUrl = '%s/create/?json' % self.serviceUri
        createVolumeBody = 'size=%d\ntag=%s' % (size, tag)
        ret = self.client.post(createVolumeUrl, createVolumeBody, "text/plain", "text/plain")
        print ret
        
    def _getPdiskEndpoint(self):
        config = self.config.configFileToDictWithFormattedKeys(self.config.configFile)
        return config['pdiskEndpoint']
