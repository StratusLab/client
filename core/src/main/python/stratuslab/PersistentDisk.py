#!/usr/bin/env python
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Centre National de la Recherche Scientifique (CNRS)
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

from datetime import datetime
from datetime import timedelta
import json
import re
from stratuslab.HttpClient import HttpClient
from urllib import urlencode
from uuid import UUID
from stratuslab.Util import printError
from socket import getfqdn
import Util
from stratuslab import Defaults
from stratuslab.Authn import UsernamePasswordCredentialsLoader
from stratuslab.Exceptions import ValidationException, ClientException,\
    ServerException
from stratuslab.ConfigHolder import ConfigHolder

class PersistentDisk(object):
    
    def __init__(self, configHolder=ConfigHolder()):
        self.pdiskUsername = None
        self.pdiskPassword = None
        self.username = None
        self.password = None
        self.pemCertificate = None
        self.pemKey = None
        self.verboseLevel = Util.NORMAL_VERBOSE_LEVEL
        self.pdiskEndpoint = None
        self.endpointSuffix = ''
        self.maxMounts = 10

        self.configHolder = configHolder
        self.configHolder.assign(self)

        # This will eventually contain the sanitized endpoint 
        # with the proper suffix attached for the authentication
        # method being used.
        self.endpoint = None

        if not self.pdiskEndpoint:
            try:
                self.pdiskEndpoint = configHolder.endpoint
            except AttributeError:
                pass
        
    def _initPDiskConnection(self):
        self.client = HttpClient(self.configHolder)
        self._addCredentials()
        self._buildFQNEndpoint()

    def _getJson(self, url):
        return self.client.get(url, accept='application/json')
        
    def _postJson(self, url, body=None, contentType='application/x-www-form-urlencoded'):
        headers, content = self.client.post(url,
                                body,
                                contentType,
                                accept='application/json')
        return headers, content.replace('\\', '')
        
    def _putJson(self, url, body, contentType='application/x-www-form-urlencoded'):
        self.client.put(url,
                        body,
                        contentType,
                        accept='application/json')
        
    def describeVolumes(self, filters={}):
        self._initPDiskConnection()
        self._printContacting()
        listVolUrl = '%s/disks/' % self.endpoint
        headers, jsonDiskList = self._getJson(listVolUrl)
        self._raiseOnErrors(headers, jsonDiskList)
        disks = json.loads(jsonDiskList)
        return self._filterDisks(disks, filters)

    def search(self, key, value):
        self._setPDiskUserCredentials()
        filtered = self.describeVolumes({key: value})
        return [disk['uuid'] for disk in filtered]

    def quarantineVolume(self, uuid):
        self._setPDiskUserCredentials()
        keyvalues = {'owner': self.pdiskUsername,
                     'quarantine': datetime.now()}
        self.updateVolume(keyvalues, uuid)
        
    def updateVolume(self, keyvalues, uuid):
        # Need to set the user as pdisk since we need to be super
        # to update pdisk metadata
        self._setPDiskUserCredentials()
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s' % (self.endpoint, uuid)
        body = urlencode(keyvalues)
        self._putJson(url, body)

    def getValue(self, key, uuid):
        self._setPDiskUserCredentials()
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s' % (self.endpoint, uuid)
        headers, jsonDisk = self._getJson(url)
        self._raiseOnErrors(headers, jsonDisk)
        disk = json.loads(jsonDisk)
        return disk[key]

    def _setPDiskUserCredentials(self):
        '''Assign the super pdisk username/password'''
        if self.pdiskUsername and self.pdiskPassword:
            return
        loader = UsernamePasswordCredentialsLoader()
        loader.load()
        self.pdiskUsername = self.persistentDiskCloudServiceUser
        self.pdiskPassword = loader.get_password(self.pdiskUsername)

    def createVolume(self, size, tag, visibility):
        self._initPDiskConnection()
        self._printContacting()
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
        self._setPDiskUserCredentials()
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s' % (self.endpoint, uuid)
        body = None
        # FIXME: We can't set body and use redirect "See Other" RPC pattern, as 
        #        there seems to be a bug in httplib2, which incorrectly approximates
        #        the accepted MIME type when doing GET on redirected resource.
        #        See: http://jira.stratuslab.eu:8080/browse/STRATUSLAB-941
#        if tag:
#            body = urlencode({'tag': tag})
        try:
            _, content = self._postJson(url, body)
        except Exception, ex:
            ex.mediaType = 'json'
            raise
        return self._getUuidFromJson(content)
    
    def rebaseVolume(self, uuid):
        # TODO: add iscow check
        self._setPDiskUserCredentials()
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s' % (self.endpoint, uuid)
        _, content = self._postJson(url)
        return self._getUuidFromJson(content)
    
    def deleteVolume(self, uuid):
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s/' % (self.endpoint, uuid)
        headers, uuid = self.client.delete(url, accept="application/json")
        self._raiseOnErrors(headers, uuid)
        return self._getUuidFromJson(uuid)
    
    def volumeExists(self, uuid):
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s/' % (self.endpoint, uuid)
        headers, _ = self.client.head(url)
        return headers.status == 200
    
    def getVolumeUsers(self, uuid):
        self._initPDiskConnection()
        self._printContacting()
        volumeUrl = '%s/disks/%s/' % (self.endpoint, uuid)
        headers, content = self._getJson(volumeUrl)
        self._raiseOnErrors(headers, content)
        count = int(json.loads(content)['count'])
        return self.maxMounts-count, self.maxMounts
    
    def hotAttach(self, node, vmId, uuid):
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s/mounts/' % (self.endpoint, uuid)
        body = {'node': node,
                'vm_id': vmId }
        headers, content = self._postJson(url, urlencode(body))
        self._raiseOnErrors(headers, content)
        return json.loads(content)['target']
    
    def hotDetach(self, node, vmId, uuid):
        self._initPDiskConnection()
        self._printContacting()
        url = '%s/disks/%s/mounts/%s-%s' % (self.endpoint, uuid, vmId, node)
        headers, content = self.client.delete(url, accept="application/json")
        self._raiseOnErrors(headers, content)
        return json.loads(content)['target']
    
    def serviceAvailable(self):
        try:
            self._initPDiskConnection()
            self._printContacting()
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

    def _addCredentials(self):
        cert = self.pemCertificate
        key = self.pemKey
        user = self.pdiskUsername or self.username
        password = self.pdiskPassword or self.password

        # Must test username/password first because there will
        # always be default values set for the certificate.
        if (user and password):
            self.endpointSuffix = '/pswd'
            self.endpointSuffix = ''
            self.client.addCredentials(user, password)
        elif (cert and key):
            self.endpointSuffix = '/cert'
            self.client.addCertificate(key, cert)
        else:
            raise ValueError('Missing credentials')

    def _buildFQNEndpoint(self):
        self.endpoint = Util.sanitizeEndpoint(self.pdiskEndpoint,
                                              Defaults.pdiskProtocol,
                                              Defaults.pdiskPort)
        self.endpoint += self.endpointSuffix
    
    @staticmethod
    def getFQNHostname(hostname):
        try:
            return getfqdn(hostname)
        except Exception:
            printError('Unable to translate endpoint "%s" to an IP address' % hostname,
                       exit=False)
        
    @staticmethod
    def isValidUuid(uuid):
        try:
            UUID(uuid)
        except ValueError:
            return False
        return True
        
    def _printContacting(self):
        self._printDetail('Accessing storage service at: %s' % self.endpoint)
        
    def _printDetail(self, message):
        Util.printDetail(message, self.verboseLevel, 1)

    def cleanQuarantine(self):
        self._setPDiskUserCredentials()

        disks = self.describeVolumes({'quarantine': ['.*']})
        threashold = self._getQuarantineThreasholdDate()

        disksToCleanUp = []

        for disk in disks:
            quarantineDate = self._parseQuarantineDate(disk['quarantine'])
            if quarantineDate < threashold:
                disksToCleanUp.append(disk)
        for disk in disksToCleanUp:
            self._printDetail('Removing disk: %s' % disk['uuid'])
            try:
                self.deleteVolume(disk['uuid'])
            except (ClientException, ServerException), ex:
                print datetime.now(), ex

    def _getQuarantineThreasholdDate(self):
        now = datetime.now()
        quarantineTime = self._getQuarantinePeriod()
        return now - timedelta(minutes=quarantineTime)

    def _getQuarantinePeriod(self):
        period, factor = self._parseQuarantinePeriod()
        return period * factor
        
    def _parseQuarantinePeriod(self):
        if not self.quarantinePeriod:
            raise ValidationException('Invalid quarantine_period parameter. Cannot be empty.')

        factor = 1
        
        if self.quarantinePeriod.isdigit():
            return int(self.quarantinePeriod), factor
        
        factors = {'m': 1, 'h': 60, 'd': 60 * 24}
        unit = self.quarantinePeriod[-1].lower()
        if unit not in factors.keys():
            raise ValidationException('Invalid quarantine_period parameter unit. Should be one of: %s.' % ', '.join(factors.keys()))

        if not self.quarantinePeriod[:-1].isdigit():
            raise ValidationException('Invalid quarantine_period parameter value. Should be integer [+ unit].')
        
        return int(self.quarantinePeriod[:-1]), factors[unit]

    def _parseQuarantineDate(self, dateString):
        return datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S.%f')
    
