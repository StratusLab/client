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
from stratuslab.Uploader import Uploader
from stratuslab.Exceptions import NetworkException
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
        
        self.vmIps = {}
        self.vmId = None
        self.sshKey = '/tmp/id_rsa_smoke_test'
        self.sshKeyPub = self.sshKey + '.pub'
        self.testsToRun = []
        self.options = {}
        
        self._fillOptions()

        self._setCloud()        

    def _fillOptions(self):
        self._fillSingleOptionParameter('repoUsername', 'app_repo_username', 'STRATUSLAB_REPO_USERNAME')
        self._fillSingleOptionParameter('repoPassword', 'app_repo_password', 'STRATUSLAB_REPO_PASSWORD')
        self._fillSingleOptionParameter('repoAddress', 'app_repo_url', 'STRATUSLAB_REPO_ADDRESS')
        self._fillSingleOptionParameter('username', 'one_username', 'STRATUSLAB_USERNAME')
        self._fillSingleOptionParameter('password', 'one_password', 'STRATUSLAB_PASSWORD')

    def _fillSingleOptionParameter(self, optionKey, configKey, envKey):
        if envKey in os.environ:
            self._setOption(optionKey,os.environ[envKey])
        elif configKey in self.config:
            self._setOption(optionKey,self.config[configKey])
        else:
            raise Exception('Missing configuration for config key %s or env var %s' % (configKey, envKey))

    def _setOption(self, key, value):
        self.options[key] = value

    def _setCloud(self):
        self.cloud = CloudConnectorFactory.getCloud()

        endpointEnv = 'STRATUSLAB_ENDPOINT'

        if endpointEnv in os.environ:
            self.cloud.setEndpoint(os.environ[endpointEnv])
        else:
            self.cloud.setFrontend(self.config.get('frontend_ip'),
                                   self.config.get('one_port'))

        self.cloud.setCredentials(self.options['username'],
                                  self.options['password'])
    
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

        testResult = unittest.TextTestRunner(verbosity=2).run(suite)
        return testResult.wasSuccessful

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
        generateSshKeyPair(self.sshKey)

        options = Runner.defaultRunOptions()
        options['username'] = self.config['one_username']
        options['password'] = self.config['one_password']
        options['userKey'] = self.sshKeyPub
        
        image = 'appliances.stratuslab.org/images/base/ubuntu-10.04-i686-base/1.0/ubuntu-10.04-i686-base-1.0.img.gz'
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

    def applianceRepositoryTest(self):
        '''Authenticate, then upload a dummy image to the appliance repository, and remove after'''
        self._testRepoConnection()
        self._uploadAndDeleteDummyImage()
        
    def _testRepoConnection(self):
        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None, self.options['repoAddress'],
                                 self.options['repoUsername'],
                                 self.options['repoUsername'])

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        try:
            opener.open(self.options['repoAddress'])
        except RuntimeError:
            raise NetworkException('Authentication to appliance repository failed')

    def _uploadAndDeleteDummyImage(self):
        dummyFile = '/tmp/stratus-dummy.img'
        self._generateDummyImage(dummyFile)

        manifest = ''
        options = self.options.copy()
        options['repoUsername'] = self.config['app_repo_username']
        options['repoPassword'] = self.config['app_repo_password']
        options['repoAddress'] = self.config['app_repo_url']
        options['uploadOption'] = ''
        uploader = Uploader(manifest, options)
        uploader.uploadFile(dummyFile, os.path.join('base',os.path.basename(dummyFile)))
        uploader.deleteFile(uploader.uploadedFile[-1])

    def _openDevNull(self):
        return open('/dev/null', 'w')

    def _generateDummyImage(self, filename, size=2):
        devNull = open('/dev/null', 'w')
        execute(['dd', 'if=/dev/zero', 'of=%s' % filename, 'bs=1000000', 'count=%s' % size],
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
                                                     
                                                