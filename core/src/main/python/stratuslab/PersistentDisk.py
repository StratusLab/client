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
import Util
from stratuslab import Defaults

class PersistentDisk(object):
    
    def __init__(self, configHolder):
        self.pdiskUsername = None
        self.pdiskPassword = None
        self.username = None
        self.password = None
        
        self.pdiskEndpoint = None

        self.configHolder = configHolder
        self.configHolder.assign(self)
        self.endpoint = None
        
    def _initPDiskConnection(self):
        self.client = HttpClient(self.configHolder)
        self.client.setHandleResponse(False)
        self._addCredentials()
        self._buildFQNEndpoint()

    def _getJson(self, url):
        headers, content = self.client.get(url, accept="application/json")
        return headers, content.replace('\\','')
        
    def _postJson(self, url, body=None, contentType='application/x-www-form-urlencoded'):
        headers, content = self.client.post(url,
                                body,
                                contentType, 
                                accept="application/json")
        return headers, content.replace('\\','')
        
    def describeVolumes(self, filters={}):
        self._initPDiskConnection()
        listVolUrl = '%s/disks/' % self.endpoint
        headers, jsonDiskList = self._getJson(listVolUrl)
        self._raiseOnErrors(headers, jsonDiskList)
        disks = json.loads(jsonDiskList)
        return self._filterDisks(disks, filters)
        
    def createVolume(self, size, tag, visibility):
        self._initPDiskConnection()
        url = '%s/disks/' % self.endpoint
        body = {'size': size, 
                'tag': tag, 
                'visibility': self._getVisibilityFromBool(visibility)}
        headers, uuid = self._postJson(url, urlencode(body))
        if headers.status == 201:
            return self._getUuidFromJson(uuid)
        self._raiseOnErrors(headers, uuid)

    def createCowVolume(self, uuid, tag):
        # TODO: add iscow check
        self._initPDiskConnection()
        self.client.setHandleResponse(True)
        url = '%s/disks/%s' % (self.endpoint, uuid)
        body = {'tag': tag}
        try:
            _, content = self._postJson(url,urlencode(body))
        except Exception, ex:
            ex.mediaType = 'json'
            raise
        return self._getUuidFromJson(content)
    
    def rebaseVolume(self, uuid):
        # TODO: add iscow check
        self._initPDiskConnection()
        self.client.setHandleResponse(True)
        url = '%s/disks/%s' % (self.endpoint, uuid)
        _, content = self._postJson(url)
        return self._getUuidFromJson(content)
    
    def deleteVolume(self, uuid):
        self._initPDiskConnection()
        url = '%s/disks/%s/' % (self.endpoint, uuid)
        headers, uuid = self.client.delete(url, accept="application/json")
        self._raiseOnErrors(headers, uuid)
        return self._getUuidFromJson(uuid)
    
    def volumeExists(self, uuid):
        self._initPDiskConnection()
        url = '%s/disks/%s/' % (self.endpoint, uuid)
        headers, _ = self.client.head(url)
        return headers.status == 200
    
    def getVolumeUsers(self, uuid):
        self._initPDiskConnection()
        volumeUrl = '%s/disks/%s/' % (self.endpoint, uuid)
        headers, content = self._getJson(volumeUrl)
        self._raiseOnErrors(headers, content)
        return int(headers['x-diskuser-remaining']), int(headers['x-diskuser-limit'])
    
    def hotAttach(self, node, vmId, uuid):
        self._initPDiskConnection()
        url = '%s/disks/%s/mounts/' % (self.endpoint, uuid)
        body = {'node': node,
                'vm_id': vmId }
        headers, content = self._postJson(url, urlencode(body))
        self._raiseOnErrors(headers, content)
        return json.loads(content)['target']
    
    def hotDetach(self, node, vmId, uuid):
        self._initPDiskConnection()
        url = '%s/disks/%s/mounts/%s-%s' % (self.endpoint, uuid, vmId, node)
        headers, content = self.client.delete(url, accept="application/json")
        self._raiseOnErrors(headers, content)
        return json.loads(content)['target']
    
    def serviceAvailable(self):
        try:
            self._initPDiskConnection()
            header, _ = self.client.head('%s' % self.endpoint)
            if header.status == 200:
                return True
            return False
        except Exception:
            return False
        
    def _raiseOnErrors(self, headers, content):
        if headers.status in (400, 411):
            raise Exception(json.loads(content)['message'])
        if headers.status != 200:
            raise Exception(headers.reason)
    
    def _getUuidFromJson(self, jsonUuid):
        return json.loads(jsonUuid)['uuid']
                
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
        self.endpoint = Util.sanitizeEndpoint(self.pdiskEndpoint, 
                                              Defaults.pdiskProtocol, 
                                              Defaults.pdiskPort)
    
    def _addCredentials(self):
        user = self.pdiskUsername or self.username
        password = self.pdiskPassword or self.password
        self.client.addCredentials(user, password)
    
    @staticmethod
    def getFQNHostname(hostname):
        endpoint = ''
        try:
            endpoint = gethostbyaddr(hostname)[0]
        except Exception:
            printError('Unable to translate endpoint "%s" to an IP address' % hostname,
                       exit=False)
        return endpoint
        
    @staticmethod
    def isValidUuid(uuid):
        try:
            UUID(uuid)
        except ValueError:
            return False
        return True
        
