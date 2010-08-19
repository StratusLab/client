import os
import traceback
import datetime
import time

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import fileGetContent
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
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
        self.sshKeyPub = self.sshKey + '.pub'
        
    def runTests(self):
        printAction('Launching smoke test')
        
        try:
            printStep('Starting VM')
            self.startVm()
            
            printStep('Ping VM')
            self.repeatCall(self.ping)
            
            printStep('Logging to VM via SSH')
            self.repeatCall(self.loginViaSsh)
            
            printStep('Shutting down VM')
            self.stopVmTest()
        except Exception, ex:
            printError(ex, exit=False)
            logFile = '/tmp/smoke-test.err'
            log = self.prepareLog(logFile)
            traceback.print_exc(file=log)
            log.close()
            printError('For details see %s' % logFile, exit=False)
            printError('Smoke test failed :-(')

        printAction('Smoke test finished')
        
    def prepareLog(self, logFile):
        log = open(logFile,'aw')
        log.write('\n'*3 + '=' * 60 + '\n')
        log.write(str(datetime.datetime.now()) + '\n')
        log.write('=' * 60 + '\n'*3)
        return log

        
    def startVm(self):
        self.buildVmTemplate()

        self.generateTestSshKeyPair()

        options = Runner.defaultRunOptions()
        options['username'] = self.config['one_username']
        options['password'] = self.config['one_password']
        options['userKey'] = self.sshKeyPub
        options['vncPort'] = 5901
        
        image = 'appliances.stratuslab.org/images/base/ubuntu-10.04-i686-base/1.0/ubuntu-10.04-i686-base-1.0.img.tar.gz'
        image = 'https://%(app_repo_username)s:%(app_repo_password)s@' + image
        image = image % self.config

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
    
    def repeatCall(self, method):
        numberOfRepetition = 30
        for _ in range(numberOfRepetition):
            failed = False
            try:
                method()
            except Exception:
                failed = True
                time.sleep(10)
            else:
                break
                
        if failed:
            printError('Failed executing method %s %s times, giving-up' % (method, numberOfRepetition), exit=False)
            raise
        
        
    def ping(self):

        for networkName, ip in self.vmIps[1:]:
            print 'Pinging %s at ip %s' % (networkName, ip)
            res = ping(ip)
            if not res:
                raise Exception('Failed to ping %s' % ip)
        
    def loginViaSsh(self):

        loginCommand = 'ls /tmp'

        for networkName, ip in self.vmIps[1:]:
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

