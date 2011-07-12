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
from urllib import urlencode
from uuid import UUID

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
        
    def createVolume(self, size, tag, visibility):
        createVolumeUrl = '%s/disks/?json' % self.pdiskEndpoint
        createVolumeBody = { 'size': size, 
                             'tag': tag, 
                             'visibility': self._getVisibilityFromBool(visibility)}
        _, uuid = self.client.post(createVolumeUrl, urlencode(createVolumeBody), 
                               'application/x-www-form-urlencoded')
        return uuid
    
    def deleteVolume(self, uuid):
        deleteVolumeUrl = '%s/disks/%s/?json&method=delete' % (self.pdiskEndpoint, uuid)
        _, uuid = self.client.post(deleteVolumeUrl, contentType='application/x-www-form-urlencoded')
        return uuid

    def _getPdiskEndpoint(self):
        config = self.config.configFileToDictWithFormattedKeys(self.config.configFile)
        return config['pdiskEndpoint']
    
    def _getVisibilityFromBool(self, visibility):
        return visibility and 'public' or 'private'
        
    @staticmethod
    def isValidUuid(uuid):
        try:
            UUID(uuid)
        except ValueError:
            return False
        return True
        