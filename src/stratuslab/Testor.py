import datetime
import inspect
import os.path
import time
import unittest
import urllib2

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Monitor import Monitor
from stratuslab.Registrar import Registrar
from stratuslab.Runner import Runner
from stratuslab.Util import execute
from stratuslab.Util import generateSshKeyPair
from stratuslab.Util import ping
from stratuslab.Util import printError
from stratuslab.Util import sshCmd

class Testor(unittest.TestCase):
    
    config = {}
    options = {}
    testNames = []
    
    def __init__(self, methodName='dummy'):
        super(Testor, self).__init__(methodName)

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

        self.testsToRun = []
        
    def dummy(self):
        pass

    def runTests(self):
        
        suite = unittest.TestSuite()
        tests = []
        if self.testNames:  
            tests = self.testNames
        else:
            tests = self._extractTestMethodNames()

        for test in tests:
            suite.addTest(Testor(test))

        unittest.TextTestRunner(verbosity=2).run(suite)

    def runMethod(self, method):
        return method()
    
    def runInstanceTest(self):
        '''Start new instance, ping it via private network and ssh into it, then stop it'''
        self._startVm()
        self._repeatCall(self._ping)
        self._repeatCall(self._loginViaSsh)
        self._stopVm()
        
    def _prepareLog(self, logFile):
        log = open(logFile,'aw')
        log.write('\n'*3 + '=' * 60 + '\n')
        log.write(str(datetime.datetime.now()) + '\n')
        log.write('=' * 60 + '\n'*3)
        return log

    def _startVm(self):
        self._generateTestSshKeyPair()

        options = Runner.defaultRunOptions()
        options['username'] = self.config['one_username']
        options['password'] = self.config['one_password']
        options['userKey'] = self.sshKeyPub
        options['endpoint'] = 'http://%s:%s/RPC2' % (self.config['frontend_ip'],
                                                     self.config['one_port'])
        
        image = 'appliances.stratuslab.org/images/base/ubuntu-10.04-i686-base/1.0/ubuntu-10.04-i686-base-1.0.img.tar.gz'
        image = 'https://%(app_repo_username)s:%(app_repo_password)s@' + image
        image = image % self.config

        runner = Runner(image, options)
        runner.runInstance()
        
        self.vmId = runner.vmId
        self.vmIps = runner.vmIps
        
        vmStarted = self.cloud.waitUntilVmRunningOrTimeout(self.vmId, 120)
        
        if not vmStarted:
            printError('Failed to start VM')
        
    def _repeatCall(self, method):
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
        
        
    def _ping(self):

        for networkName, ip in self.vmIps[1:]:
            print 'Pinging %s at ip %s' % (networkName, ip)
            res = ping(ip)
            if not res:
                raise Exception('Failed to ping %s' % ip)
        
    def _loginViaSsh(self):

        loginCommand = 'ls /tmp'

        for networkName, ip in self.vmIps[1:]:
            print 'SSHing into machine via address %s at ip %s' % (networkName, ip)
            res = sshCmd(loginCommand, ip, self.sshKey)
            if res:
                raise Exception('Failed to SSH into machine for %s with return code %s' % (ip, res))
        
    def _stopVm(self):
        vmStopped = self.cloud.vmStop(self.vmId)
        
        if not vmStopped:
            printError('Failing to stop VM')

    def _generateTestSshKeyPair(self):
        generateSshKeyPair(self.sshKey)
        execute('chown %s %s' % (self.config['one_username'], self.sshKey), shell=True)

    def applianceRepositoryTest(self):
        '''Authenticate, then upload a dummy image to the appliance repository, and remove after'''
        self._testRepoConnection()
        self._uploadAndDeleteDummyImage()
        
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

    def _uploadAndDeleteDummyImage(self):
        devNull = open('/dev/null', 'w')

        dummyFile = '/tmp/stratus-dummy.img'
        self._generateDummyImage(dummyFile)

        baseCurlCmd = ['curl', '-u', '%s:%s' % (self.config.get('app_repo_username'), self.config.get('app_repo_password'))]

        uploadCmd = baseCurlCmd + ['-T', dummyFile, self.repoUrl, '-k']
        ret = execute(uploadCmd, stdout = devNull, stderr = devNull)

        if ret != 0:
            raise Exception('Failed to upload dummy image')

        deleteCmd = baseCurlCmd + [ '-X', 'DELETE', '%s/%s' % (self.repoUrl, os.path.basename(dummyFile)), '-k', '-q']
        execute(tuple(deleteCmd), stdout = devNull, stderr = devNull)

    def _generateDummyImage(self, filename, size=2):
        devNull = open('/dev/null', 'w')
        execute(['dd', 'if=/dev/zero', 'of=%s' % filename, 'bs=1M', 'count=%s' % size],
        stdout=devNull, stderr=devNull)
        devNull.close()

    def registrarTest(self):
        '''Register a new node with ONE server, check that it is properly registered and remove it'''
        options = self.options.copy()
        options['infoDriver'] = 'kvm'
        options['virtDriver'] = 'kvm'
        options['transfertDriver'] = 'nfs'
        options['password'] = self.config['one_password']
        registrar = Registrar(options, self.config)
        hostname = 'registrar.ip.test'
        id = registrar.register([hostname])
        monitor = Monitor(options, self.config)
        info = monitor.monitor([id])[0]
        self.assertEqual(hostname, info.name)
        registrar.deregister(hostname)
        self.assertRaises(Exception, monitor.monitor,[id])

    def listTests(self):
        print 'Available tests:'
        for testName, testDoc in self._extractTestDescriptions():
            print '    - %s: %s' % (testName, testDoc)

    def _extractTestDescriptions(self):
        methods = []
        for attrib in self.__class__.__dict__:
            if self._isTestMethod(attrib):
                methods.append((attrib,self.__class__.__dict__[attrib].__doc__))
        return methods
    
    def _extractTestMethodNames(self):
        methods = []
        for attrib in self.__class__.__dict__:
            if self._isTestMethod(attrib):
                methods.append(attrib)
        return methods
    
    def _isTestMethod(self, attrib):
        return inspect.ismethod(getattr(self, attrib)) and \
               (attrib.lower().startswith('test') or attrib.lower().endswith('test')) and \
               not attrib.startswith('_')
                                                     
                                                