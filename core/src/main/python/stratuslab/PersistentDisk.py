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
import re
from stratuslab.HttpClient import HttpClient
from urllib import urlencode
from uuid import UUID
from stratuslab.Util import printError

class PersistentDisk(object):
    
    def __init__(self, configHolder):
        self.pdiskEndpoint = 'https://%(pdiskEndpoint)s:%(pdiskPort)d'
        self.client = HttpClient(configHolder)
        self.client.useCredentials(True)
        self.config = configHolder
        self._buildFQNEndpoint()
        
    def volumeList(self, filters={}):
        listVolUrl = '%s/disks/?json' % self.pdiskEndpoint
        _, jsonDiskList = self.client.get(listVolUrl, accept='text/plain')
        disks = json.loads(jsonDiskList)
        return self._filterDisks(disks, filters)
        
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
    
    def _getVisibilityFromBool(self, visibility):
        return visibility and 'public' or 'private'

    def _filterDisks(self, disks, filters):
        availableDisk = []
        for disk in disks:
            addDisk = True
            for propertyName, searchedValue in filters.items():
                diskProperty = disk.get(propertyName, None)
                if not diskProperty:
                    addDisk = False
                    break
                for value in searchedValue:
                    if not re.search(value, diskProperty):
                        addDisk = False
                        break
            if addDisk:
                availableDisk.append(disk)
        return availableDisk
    
    def _buildFQNEndpoint(self):
        self._checkEndpoint();
        self.pdiskEndpoint = self.pdiskEndpoint % {'pdiskEndpoint': self.config.pdiskEndpoint,
                                                   'pdiskPort': self.config.pdiskPort }
        
    def _checkEndpoint(self):
        if not self.config.pdiskEndpoint.lstrip().rstrip():
            printError('No valid persistent disk endpoint found', exitCode=1, exit=True)
                        
    def _removeTrailingSlash(self, string):
        return string[:-1]
        
    @staticmethod
    def isValidUuid(uuid):
        try:
            UUID(uuid)
        except ValueError:
            return False
        return True
        