#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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
import sys
import time
from random import randint

from stratuslab.Util import execute
from stratuslab.Util import sshCmd

# NOT USED ANYMORE!!
class QEmuConnector(object):
    '''Connector to run a machine in QEmu'''
    
    def __init__(self):
        self.host = None
        self.port = None
        self.sshKey = None
        self.qemuProcess = None

    def setFrontend(self, host, *args, **kwargs):
        self.host = host
        self.port = randint(2000, 10000)

    def setCredentials(self, key, *args, **kwargs):
        self.sshKey = key

    # -------------------------------------------
    #    Virtual machine management
    # -------------------------------------------

    def vmStart(self, image, *args, **kwargs):
        stdstream = open('/dev/null', 'w')
        self.qemuProcess = execute('qemu', '-nographic', image, '-redir',
                                        'tcp:%s::22' % self.port, noWait=True, 
                                        stdout=stdstream, stderr=stdstream)
        stdstream.close()
        return 1

    def vmStop(self, *args, **kwargs):
        sshCmd('shutdown -h now', self.host, self.sshKey, self.port)

    def getVmIp(self, *args, **kwargs):
        return {'private': self.host,
                'public': self.host }

    def getVmSshPort(self, *args, **kwargs):
        return self.port

    def waitUntilVmRunningOrTimeout(self, vmId, timeout, ticks=True):
        stdstream = open('/dev/null', 'w')
        start = time.time()
        vmBooting = True
        while vmBooting:
            vmBooting = sshCmd('exit 42', self.host, self.sshKey, self.port,
                                        stdout=stdstream, stderr=stdstream) != 42

            if ticks:
                sys.stdout.flush()
                sys.stdout.write('.')
            time.sleep(1)

            if time.time() - start > timeout:
                return False

        return True

    def createMachineTemplate(self, imagePath, template):
        return imagePath

    def addPublicInterface(self, vmTpl):
        return vmTpl
    
