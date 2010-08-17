import os
import traceback

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import fileGetContent
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import modulePath
from stratuslab.Util import execute
from stratuslab.Util import sshCmd
from stratuslab.Util import ping
from stratuslab.Runner import Runner


class Testor(object):
    
    def __init__(self, config, options):
        self.config = config
        self.options = options

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(self.config.get('one_username'),
                                  self.config.get('one_password'))
        
        # Attributes initialization
        self.vmTemplate = None
        self.vmIps = {}
        self.vmId = None
        self.sshKey = '/tmp/id_rsa_smoke_test'
        
    def runTests(self):
        printAction('Launching smoke test')
        
        try:
            printStep('Starting VM')
            self.startVm()
            
            printStep('Ping VM')
            self.ping()
            
            printStep('Logging to VM via SSH')
            self.loginViaSsh()
            
            printStep('Shutting down VM')
            self.stopVmTest()
        except Exception, ex:
            printError(ex, exit=False)
            logFile = '/tmp/smoke-test.err'
            stack = traceback.format_stack()
            log = open(logFile,'aw')
            log.write('\n'.join(stack))
            log.close()
            printError('For details see %s' % logFile, exit=False)
            printError('Smoke test failed :-(')

        printAction('Smoke test finished')
        
    def startVm(self):
        self.buildVmTemplate()

        self.generateTestSshKeyPair()

        options = Runner.defaultRunOptions()
        options['username'] = self.config['one_username']
        options['password'] = self.config['one_password']
        options['userKey'] = self.sshKey

        image = 'https://appliances.stratuslab.org/images/base/centos-5.5-i386-base/1.0/centos-5.5-i386-base-1.0.img.tar.gz'
        runner = Runner(image, options, self.config)
        runner.runInstance()
        
        self.vmId = runner.vmId
        self.vmIps = runner.vmIps
        
        vmStarted = self.cloud.waitUntilVmRunningOrTimeout(self.vmId, 120)
        
        if not vmStarted:
            printError('Failed to start VM')
        else:
            print 'Successfully started image', self.vmId
        
    def buildVmTemplate(self):
        self.vmTemplate = fileGetContent(self.options.vmTemplate) % self.config
    
    def ping(self):

        for networkName, ip in self.vmIps:
            print 'Pinging %s at ip %s' % (networkName, ip)
            res = ping(ip)
            if res:
                raise Exception('Failed to ping %s with return code %s' % (ip, res))
        
    def loginViaSsh(self):

        loginCommand = 'ls /tmp'

        for networkName, ip in self.vmIps:
            print 'SSHing into machine at via address %s at ip %s' % (networkName, ip)
            res = sshCmd(loginCommand, ip, self.config.get('node_private_key'))
            if res:
                raise Exception('Failed to SSH into machine for %s with return code %s' % (ip, res))
        
    def stopVmTest(self):
        vmStopped = self.cloud.vmStop(self.vmId)
        
        if not vmStopped:
            printError('Failing to stop VM')

    def generateTestSshKeyPair(self):
        self.generateSshKeyPair(self.sshKey)
        execute('chown %s %s' % (self.config['one_username'], self.sshKey), shell=True)

    def generateSshKeyPair(self, key):
        try:
            os.remove(key)
        except(OSError):
            pass
        sshCmd = 'ssh-keygen -f %s -N "" -q' % key
        execute(sshCmd, shell=True)
