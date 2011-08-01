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
from socket import gethostbyaddr

class PersistentDisk(object):
    REQUEST_SUCCESS = '1'
    REQUEST_FAILLED = '0'
    USAGE_SEPARATOR = '#'
    
    def __init__(self, configHolder):
        self.structEndpoint = 'https://%(pdiskEndpoint)s:%(pdiskPort)d'
        self.config = configHolder
        self.pdiskEndpoint = None
        
    def _initPDiskConnection(self):
        self.client = HttpClient(self.config)
        self._addCredentials()
        self._buildFQNEndpoint()
        
    def volumeList(self, filters={}):
        self._initPDiskConnection()
        listVolUrl = '%s/disks/?json' % self.pdiskEndpoint
        _, jsonDiskList = self.client.get(listVolUrl, accept='text/plain')
        disks = json.loads(jsonDiskList)
        return self._filterDisks(disks, filters)
        
    def createVolume(self, size, tag, visibility):
        self._initPDiskConnection()
        createVolumeUrl = '%s/disks/?json' % self.pdiskEndpoint
        createVolumeBody = { 'size': size, 
                             'tag': tag, 
                             'visibility': self._getVisibilityFromBool(visibility)}
        _, uuid = self.client.post(createVolumeUrl, urlencode(createVolumeBody), 
                               'application/x-www-form-urlencoded')
        return uuid
    
    def deleteVolume(self, uuid):
        self._initPDiskConnection()
        deleteVolumeUrl = '%s/disks/%s/?json&method=delete' % (self.pdiskEndpoint, uuid)
        _, uuid = self.client.post(deleteVolumeUrl, contentType='application/x-www-form-urlencoded')
        return uuid
    
    def volumeExists(self, uuid):
        filter = {'uuid': [uuid,]}
        return len(self.volumeList(filter)) == 1
    
    def remainingUsersVolume(self, uuid):
        self._initPDiskConnection()
        volumeUrl = '%s/disks/%s/' % (self.pdiskEndpoint, uuid)
        volumeBody = {'available': 1}
        _, res = self.client.post(volumeUrl, urlencode(volumeBody), 'application/x-www-form-urlencoded')
        return int(res)
        
    def attachVolumeRequest(self, uuid, cloudEndpoind, vmId):
        self._initPDiskConnection()
        volumeUrl = '%s/disks/%s/' % (self.pdiskEndpoint, uuid)
        cloudEndpoind = self.getFQNHostname(cloudEndpoind)
        volumeBody = {'attach': '%s%s%s' % (cloudEndpoind, self.USAGE_SEPARATOR, vmId)}
        _, res = self.client.post(volumeUrl, urlencode(volumeBody), 'application/x-www-form-urlencoded')
        return res == self.REQUEST_SUCCESS
        
    def detachVolumeRequest(self, cloudEndpoind, vmId):
        # If no endpoint set, assume there is nothing to do
        if not self.config.pdiskEndpoint:
            return
        if not self._checkServiceStatus():
            return
        volumeUrl = '%s/disks/?method=delete' % self.pdiskEndpoint
        cloudEndpoind = self.getFQNHostname(cloudEndpoind)
        volumeBody = {'detach': '%s%s%s' % (cloudEndpoind, self.USAGE_SEPARATOR, vmId)}
        _, res = self.client.post(volumeUrl, urlencode(volumeBody), 'application/x-www-form-urlencoded')
        return res
    
    def _checkServiceStatus(self):
        try:
            self._initPDiskConnection()
            self.client.get('%s?json' % self.pdiskEndpoint)
            return True
        except Exception:
            return False
        
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
        if self.pdiskEndpoint:
            return
        self._checkEndpoint();
        self.pdiskEndpoint = self.structEndpoint % self.config.options
        
    def _checkEndpoint(self):
        if not self.config.pdiskEndpoint.lstrip().rstrip():
            printError('No valid persistent disk endpoint found', exitCode=1, exit=True)
                        
    def _removeTrailingSlash(self, string):
        return string[:-1]
    
    def _addCredentials(self):
        user = self.config.options.get('pdiskUsername', '') or self.config.username
        password = self.config.options.get('pdiskPassword', '') or self.config.password
        self.client.addCredentials(user, password)
    
    @staticmethod
    def getFQNHostname(hostname):
        endpoint = ''
        try:
            endpoint = gethostbyaddr(hostname)[0]
        except Exception:
            printError('Unable to translate endpoint %s to it IP address' % hostname, 
                       exitCode=1, exit=True)
        return endpoint
        
    @staticmethod
    def isValidUuid(uuid):
        try:
            UUID(uuid)
        except ValueError:
            return False
        return True
        