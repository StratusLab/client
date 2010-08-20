import os.path
import datetime
import os
import time
import traceback
from distutils.command.upload import upload
import urllib2

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Runner import Runner
from stratuslab.Util import execute
from stratuslab.Util import ping
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import sshCmd


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
        self.vmIps = {}
        self.vmId = None
        self.sshKey = '/tmp/id_rsa_smoke_test'
        self.sshKeyPub = self.sshKey + '.pub'
        self.repoUrl = 'http://%s/images/base/' % self.config.get('app_repo_url')
        
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

            printStep('Appliance repository authentication')
            self._testRepoConnection()

            printStep('Uploading dummy image')
            self._testUploadDummyImage()

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
        
    def repeatCall(self, method):
        numberOfRepetition = 60
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
            print 'SSHing into machine via address %s at ip %s' % (networkName, ip)
            res = sshCmd(loginCommand, ip, self.sshKey)
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

    def _testRepoConnection(self):
        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None, self.repoUrl,
                                 self.config.get('app_repo_username'),
                                 self.config.get('app_repo_password'))

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        try:
            opener.open(self.repoUrl)
        except RuntimeError:
            raise Exception('Authentication to appliance repository failed')

    def _generateDummyImage(self, filename, size=2):
        devNull = open('/dev/null', 'w')
        execute('dd', 'if=/dev/zero', 'of=%s' % filename, 'bs=1M', 'count=%s' % size,
        stdout=devNull, stderr=devNull)
        devNull.close()

    def _testUploadDummyImage(self):
        devNull = open('/dev/null', 'w')

        dummyFile = '/tmp/stratus-dummy.img'
        self._generateDummyImage(dummyFile)

        baseCurlCmd = ['curl', '-u', '%s:%s' % (self.config.get('app_repo_username'), self.config.get('app_repo_password'))]

        uploadCmd = baseCurlCmd + ['-T', dummyFile, self.repoUrl, '-k']
        ret = execute(*uploadCmd, stdout = devNull, stderr = devNull)

        if ret != 0:
            raise Exception('Failed to upload dummy image')

        deleteCmd = baseCurlCmd + [ '-X', 'DELETE', '%s/%s' % (self.repoUrl, os.path.basename(dummyFile)), '-k', '-q']
        execute(*deleteCmd, stdout = devNull, stderr = devNull)
