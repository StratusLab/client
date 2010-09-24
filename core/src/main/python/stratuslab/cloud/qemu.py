import sys
import time
from random import randint

from stratuslab.Util import execute
from stratuslab.Util import sshCmd


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
    