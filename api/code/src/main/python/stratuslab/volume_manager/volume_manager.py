#!/usr/bin/env python
#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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

from socket import getfqdn

from uuid import UUID
from stratuslab.Util import printError
from stratuslab.ConfigHolder import ConfigHolder


class VolumeManager(object):
    """
    Provides an abstract interface for different volume manager
    implementations.  The initial interface is exactly the same
    public interface presented by the old PersistentDisk class.
    """

    def __init__(self, config_holder=None):
        if config_holder is None:
            config_holder = ConfigHolder()

        self.configHolder = config_holder

    def describeVolumes(self, filters={}):
        raise NotImplementedError()

    def search(self, key, value):
        raise NotImplementedError()

    def quarantineVolume(self, uuid):
        raise NotImplementedError()

    def updateVolume(self, keyvalues, uuid):
        raise NotImplementedError()

    def updateVolumeAsUser(self, keyvalues, uuid):
        raise NotImplementedError()

    def getValue(self, key, uuid):
        raise NotImplementedError()

    def createVolume(self, size, tag, visibility):
        raise NotImplementedError()

    def createVolumeFromUrl(self, size, tag, visibility, imageUrl, bytes, sha1):
        raise NotImplementedError()

    def createCowVolume(self, uuid, tag):
        raise NotImplementedError()

    def rebaseVolume(self, uuid):
        raise NotImplementedError()

    def deleteVolume(self, uuid):
        raise NotImplementedError()

    def volumeExists(self, uuid):
        raise NotImplementedError()

    def getVolumeUsers(self, uuid):
        raise NotImplementedError()

    def getVolumeUserCount(self, uuid):
        raise NotImplementedError()

    def getTurl(self, uuid):
        raise NotImplementedError()

    def hotAttach(self, node, vmId, uuid):
        raise NotImplementedError()

    def hotDetach(self, vmId, uuid):
        raise NotImplementedError()

    def downloadVolume(self, uuid, filename):
        raise NotImplementedError()

    def uploadVolume(self, filename):
        raise NotImplementedError()

    def serviceAvailable(self):
        raise NotImplementedError()

    def cleanQuarantine(self):
        raise NotImplementedError()

    @staticmethod
    def getFQNHostname(hostname):
        """
        Returns the fully qualified domain name for the given hostname.
        If it isn't possible to find it, an error is printed and the
        original hostname is returned.
        """
        try:
            return getfqdn(hostname)
        except Exception:
            printError('Unable to translate endpoint "%s" to an IP address' % hostname,
                       exit=False)
            return hostname

    @staticmethod
    def isValidUuid(uuid):
        try:
            UUID(uuid)
        except ValueError:
            return False
        return True

