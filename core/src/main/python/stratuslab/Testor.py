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
import datetime
import inspect
import os.path
import time
import unittest
import urllib2

from stratuslab.Monitor import Monitor
from stratuslab.Registrar import Registrar
from stratuslab.Runner import Runner
from stratuslab.Uploader import Uploader
from stratuslab.Exceptions import NetworkException
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Exceptions import ExecutionException
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Util import execute
from stratuslab.Util import generateSshKeyPair
from stratuslab.Util import ping
from stratuslab.Util import printError
from stratuslab.Util import sshCmd
import Util

class Testor(unittest.TestCase):
    
    configHolder = None
    testNames = []
    
    def __init__(self, methodName='dummy'):
        super(Testor, self).__init__(methodName)
        
        self.vmIds = []
        self.sshKey = '/tmp/id_rsa_smoke_test'
        self.sshKeyPub = self.sshKey + '.pub'
        self.testsToRun = []
        
        Testor.configHolder.assign(self)
        self._setEnvVars()

    def _setEnvVars(self):
        self._setSingleEnvVar('appRepoUsername', 'STRATUSLAB_REPO_USERNAME')
        self._setSingleEnvVar('appRepoPassword', 'STRATUSLAB_REPO_PASSWORD')
        self._setSingleEnvVar('appRepoUrl', 'STRATUSLAB_REPO_ADDRESS')
        self._setSingleEnvVar('username', 'STRATUSLAB_USERNAME')
        self._setSingleEnvVar('password', 'STRATUSLAB_PASSWORD')
        self._fillEndpointOption()
        
    def _setSingleEnvVar(self, field, env):
        if env in os.environ:
            setattr(self, field, os.environ[env])

    def _setOption(self, key, value):
        Testor.configHolder.options[key] = value

    def _fillEndpointOption(self):
        if Util.envEndpoint in os.environ:
            return
        if not self.frontendIp:
            raise ConfigurationException('Missing environment variable %s or configuration parameter frontend_ip' % Util.envEndpoint)
        os.environ[Util.envEndpoint] = self.frontendIp

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
        return testResult.wasSuccessful()

    def runMethod(self, method):
        return method()
    
    def runInstancePublicNetworkTest(self):
        '''Start new instance, ping it via public network and ssh into it, then stop it.'''
        self._runInstanceTest()
        
    def runInstanceLocalNetworkTest(self):
        '''Start new instance, ping it via local network and ssh into it, then stop it.'''
        self._runInstanceTest(True)
        
    def _runInstanceTest(self, withLocalNetwork=False):
        runner = self._startVm(withLocalNetwork)
        self._repeatCall(self._ping, runner)
        self._repeatCall(self._loginViaSsh, runner)
        self._stopVm(runner)
        
    def _prepareLog(self, logFile):
        log = open(logFile,'aw')
        log.write('\n'*3 + '=' * 60 + '\n')
        log.write(str(datetime.datetime.now()) + '\n')
        log.write('=' * 60 + '\n'*3)
        return log

    def _startVm(self, withLocalNetwork=False):
        generateSshKeyPair(self.sshKey)

        options = Runner.defaultRunOptions()
        options['username'] = self.oneUsername
        options['password'] = self.proxyOneadminPassword
        options['userKey'] = self.sshKeyPub
        options['verboseLevel'] = self.verboseLevel

        if withLocalNetwork:
            options['isLocalIp'] = True

        configHolder = ConfigHolder(options)
        #image = 'http://appliances.stratuslab.org/images/base/ttylinux-9.5-i486-base/1.0/ttylinux-9.5-i486-base-1.0.img.gz'
        image = 'http://appmirror-grnet.stratuslab.org/images/base/ttylinux-9.5-i486-base/1.0/ttylinux-9.5-i486-base-1.0.img.gz'
        runner = Runner(image, configHolder)
        self.vmIds = runner.runInstance()        
        
        for id in self.vmIds:
            vmStarted = runner.waitUntilVmRunningOrTimeout(id)            
            if not vmStarted:
                printError('Failed to start VM id: %s' % id)
                
        return runner

    def _repeatCall(self, method, args=[]):
        numberOfRepetition = 60
        for _ in range(numberOfRepetition):
            failed = False
            try:
                if args:
                    method(args)
                else:
                    method()
            except ExecutionException:
                failed = True
                time.sleep(10)
            else:
                break
                
        if failed:
            printError('Failed executing method %s %s times, giving-up' % (method, numberOfRepetition), exit=False)
            raise
        
    def _ping(self, runner):

        for vmId in self.vmIds:
            _, ip = runner.getNetworkDetail(vmId)
            res = ping(ip)
            if not res:
                raise ExecutionException('Failed to ping %s' % ip)
        
    def _loginViaSsh(self, runner):

        loginCommand = 'ls /tmp'

        for vmId in self.vmIds:
            _, ip = runner.getNetworkDetail(vmId)
            res = sshCmd(loginCommand, ip, self.sshKey)
            if res:
                raise ExecutionException('Failed to SSH into machine for %s with return code %s' % (ip, res))

    def _stopVm(self, runner):
        runner.killInstances(self.vmIds)

    def applianceRepositoryTest(self):
        '''Authenticate, then upload a dummy image to the appliance repository, and remove after'''

        self._checkAttributePresent(['appRepoUsername', 'appRepoPassword'])
        self._testRepoConnection()
        self._uploadAndDeleteDummyImage()

    def _checkAttributePresent(self, attrs):
        for attr in attrs:
            if attr not in self.__dict__:
                raise Exception('Missing attribute %s. Missing an option argument?' % attr)
            
        
    def _testRepoConnection(self):
        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None,
                                 self.appRepoUrl,
                                 self.appRepoUsername,
                                 self.appRepoPassword)

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        try:
            opener.open(self.appRepoUrl)
        except RuntimeError:
            raise NetworkException('Authentication to appliance repository failed')

    def _uploadAndDeleteDummyImage(self):
        dummyFile = '/tmp/stratus-dummy.img'
        self._generateDummyImage(dummyFile)

        manifest = ''
        options = self.configHolder.options.copy()
        options['repoUsername'] = self.appRepoUsername
        options['repoPassword'] = self.appRepoPassword
        options['repoAddress'] = self.appRepoUrl
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
        configHolder = self.configHolder.copy()
        configHolder.options['infoDriver'] = 'kvm'
        configHolder.options['virtDriver'] = 'kvm'
        configHolder.options['transfertDriver'] = 'nfs'
        configHolder.options['username'] = self.oneUsername
        configHolder.options['password'] = self.proxyOneadminPassword
        registrar = Registrar(configHolder)
        hostname = 'registrar.ip.test'
        id = registrar.register([hostname])
        monitor = Monitor(configHolder)
        info = monitor.nodeDetail([id])[0]
        self.assertEqual(hostname, info.name)
        registrar.deregister(hostname)
        self.assertRaises(Exception, monitor.nodeDetail,[id])

    def listAvalableTests(self):
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
                                                     
                                                
