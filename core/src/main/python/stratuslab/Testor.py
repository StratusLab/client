#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, SixSq Sarl
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
from stratuslab.Creator import Creator
from stratuslab.Exceptions import NetworkException, OneException
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Exceptions import ExecutionException
from stratuslab.Exceptions import InputException
from stratuslab.ConfigHolder import ConfigHolder
import Util
from stratuslab.marketplace.Downloader import Downloader
import stratuslab.ClaudiaTest as ClaudiaTest
import stratuslab.ClusterTest as ClusterTest
import stratuslab.RegistrationTest as RegistrationTest

VM_START_TIMEOUT = 5 * 60 # 5 min

class Testor(unittest.TestCase):

    configHolder = None
    testNames = []

    def __init__(self, methodName='dummy'):
        super(Testor, self).__init__(methodName)

        self.vmIds = []
        self.sshKey = '/tmp/id_rsa_smoke_test'
        self.sshKeyPub = self.sshKey + '.pub'
        self.testsToRun = []
        self.quotaCpu = 2
        self.runner = None

        Testor.configHolder.assign(self)
        self._setFieldsFromEnvVars()

        self.image = 'http://appliances.stratuslab.org/images/base/ttylinux-9.7-i486-base/1.2/ttylinux-9.7-i486-base-1.2.img.gz'

    def _setFieldsFromEnvVars(self):
        self._setSingleFieldFromEnvVar('apprepoUsername', 'STRATUSLAB_APPREPO_USERNAME')
        self._setSingleFieldFromEnvVar('apprepoPassword', 'STRATUSLAB_APPREPO_PASSWORD')
        self._setSingleFieldFromEnvVar('apprepoEndpoint', 'STRATUSLAB_APPREPO_ENDPOINT')
        self._setSingleFieldFromEnvVar('username', 'STRATUSLAB_USERNAME')
        self._setSingleFieldFromEnvVar('password', 'STRATUSLAB_PASSWORD')
        self._setSingleFieldFromEnvVar('requestedIpAddress', 'STRATUSLAB_REQUESTED_IP_ADDRESS')
        self._setSingleFieldFromEnvVar('p12Certificate', 'STRATUSLAB_P12_CERTIFICATE')
        self._setSingleFieldFromEnvVar('p12Password', 'STRATUSLAB_P12_PASSWORD')
        self._exportEndpointIfNotInEnv()
        self._setSingleFieldFromEnvVar('endpoint', 'STRATUSLAB_ENDPOINT')

    def _setSingleFieldFromEnvVar(self, field, env):
        if env in os.environ:
            setattr(self, field, os.environ[env])

    def setupUp(self):
        self.vmIds = []

    def _exportEndpointIfNotInEnv(self):
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

        self._excludeTests(tests)

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
        self._runInstanceTest(withLocalNetwork=True,
                                cmdToRun='ping -c 2 www.google.com')

    def runInstanceRequestedNetworkTest(self):
        '''Start new instance, ping it via requested IP address and ssh into it, then stop it.'''

        self._checkAttributePresent(['requestedIpAddress'])
        if not self.requestedIpAddress:
            raise InputException('Missing definition for requested IP. Are you not missing --requested-ip-address?')
        runner = self._startVm(requestedIpAddress=self.requestedIpAddress)

        _, allocatedIp = runner.getNetworkDetail(runner.vmIds[0])

        self.assertEqual(self.requestedIpAddress, allocatedIp)

        self._repeatCall(self._ping, runner)
        self._repeatCall(self._loginViaSsh, runner, '/bin/true')
        self._stopVm(runner)

    def exceedCpuQuotaTest(self):
        '''Start x instances, where x is the cpu quota +1, then stop them.'''

        print 'Current cpu quota: %s, starting as many +1' % self.quotaCpu
        try:
            self._startVm(instanceNumber=int(self.quotaCpu)+1)
        except OneException, ex:
            message="Cpu quota exceeded (Quota: %s, Used: %s.0, asked: 1.0)." % (self.quotaCpu, self.quotaCpu)
            self.assertTrue(message in ex.message, 'Quota not working, got %s expected %s' % (ex.message, message))
        else:
            self.fail('Quota not enforced')

        self._createRunner().killInstances(self.runner.vmIds)
        
    def _excludeTests(self, tests):
        if self.testsToExclude:
            for test in self.testsToExclude.split(','):
                try:
                    tests.remove(test)
                except ValueError:
                    print "WARNING: Test '%s' not in a list of defined tests." % test

    def _runInstanceTest(self, withLocalNetwork=False, cmdToRun='/bin/true'):
        runner = self._startVm(withLocalNetwork)
        self._repeatCall(self._ping, runner)
        self._repeatCall(self._loginViaSsh, runner, cmdToRun)
        self._stopVm(runner)

    def _prepareLog(self, logFile):
        log = open(logFile, 'aw')
        log.write('\n' * 3 + '=' * 60 + '\n')
        log.write(str(datetime.datetime.now()) + '\n')
        log.write('=' * 60 + '\n' * 3)
        return log

    def _startVm(self, withLocalNetwork=False, requestedIpAddress=None, instanceNumber=1):
        self.runner = self._createRunner(withLocalNetwork, requestedIpAddress)
        self.runner.instanceNumber = instanceNumber

        vmIds = self.runner.runInstance()
        self.vmIds.extend(vmIds)

        for id in vmIds:
            vmStarted = self.runner.waitUntilVmRunningOrTimeout(id, VM_START_TIMEOUT)
            if not vmStarted:
                error = 'Failed to start VM id: %s' % id
                Util.printError(error, exit=False)
                raise OneException(error)

        return self.runner

    def _createRunner(self, withLocalNetwork=False, requestedIpAddress=None):
        Util.generateSshKeyPair(self.sshKey)

        options = Runner.defaultRunOptions()
        options['username'] = self.testUsername
        options['password'] = self.testPassword
        options['userPublicKeyFile'] = self.sshKeyPub
        options['verboseLevel'] = self.verboseLevel
        options['specificAddressRequest'] = requestedIpAddress

        if withLocalNetwork:
            options['isLocalIp'] = True

        configHolder = ConfigHolder(options)
        return Runner(self.image, configHolder)

    def _repeatCall(self, method, *args):
        numberOfRepetition = 60
        for _ in range(numberOfRepetition):
            failed = False
            try:
                if args:
                    method(*args)
                else:
                    method()
            except ExecutionException:
                failed = True
                time.sleep(10)
            else:
                break

        if failed:
            Util.printError('Failed executing method %s %s times, giving-up' % (method, numberOfRepetition), exit=False)
            raise

    def _ping(self, runner):

        for vmId in self.vmIds:
            _, ip = runner.getNetworkDetail(vmId)
            res = Util.ping(ip)
            if not res:
                raise ExecutionException('Failed to ping %s' % ip)

    def _loginViaSsh(self, runner, cmd):

        for vmId in self.vmIds:
            _, ip = runner.getNetworkDetail(vmId)
            res = Util.sshCmd(cmd, ip, self.sshKey)
            if res:
                raise ExecutionException('Failed to SSH into machine for %s with return code %s' % (ip, res))

    def _stopVm(self, runner):
        runner.killInstances(self.vmIds)

    def applianceRepositoryTest(self):
        '''Authenticate, then upload a dummy image to the appliance repository, and remove after'''

        self._checkAttributePresent(['apprepoUsername', 'apprepoPassword'])
        self._testRepoConnection()
        self._uploadAndDeleteDummyImage()

    def _checkAttributePresent(self, attrs):
        for attr in attrs:
            if attr not in self.__dict__:
                raise Exception('Missing attribute %s. Missing an option argument?' % attr)


    def _testRepoConnection(self):
        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None,
                                 self.apprepoEndpoint,
                                 self.apprepoUsername,
                                 self.apprepoPassword)

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        try:
            opener.open(self.apprepoEndpoint)
        except RuntimeError:
            raise NetworkException('Authentication to appliance repository failed')

    def _uploadAndDeleteDummyImage(self):
        dummyFile = '/tmp/stratus-dummy.img'
        self._generateDummyImage(dummyFile)

        manifest = ''
        configHolder = Testor.configHolder.copy()
        configHolder.set('apprepoUsername', self.apprepoUsername)
        configHolder.set('apprepoPassword', self.apprepoPassword)
        configHolder.set('apprepoEndpoint',  self.apprepoEndpoint)
        configHolder.set('uploadOption', '')
        uploader = Uploader(manifest, configHolder)
        uploader.uploadFile(dummyFile, os.path.join('base', os.path.basename(dummyFile)))
        uploader.deleteFile(uploader.uploadedFile[-1])

    def _openDevNull(self):
        return open('/dev/null', 'w')

    def _generateDummyImage(self, filename, size=2):
        devNull = open('/dev/null', 'w')
        Util.execute(['dd', 'if=/dev/zero', 'of=%s' % filename, 'bs=1000000', 'count=%s' % size],
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
        self.assertRaises(Exception, monitor.nodeDetail, [id])

    def listAvalableTests(self):
        print 'Available tests:'
        for testName, testDoc in self._extractTestDescriptions():
            print '    - %s: %s' % (testName, testDoc)

    def _extractTestDescriptions(self):
        methods = []
        for attrib in self.__class__.__dict__:
            if self._isTestMethod(attrib):
                methods.append((attrib, self.__class__.__dict__[attrib].__doc__))
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

    def createImageTest(self):
        '''Create a machine image based on a given one.'''
        image = 'OMd8M7ixG3toGqm8C1MhUphMJWF'
        creator = self._createCreator(image)

        newImage = creator.showName()
        newImageUri = '%s/%s'%(creator.apprepoEndpoint, newImage)

        self._deleteImageAndManifestFromAppRepo(newImageUri)

        try:
            creator.create()
        finally:
            creator._stopMachine()

        assert creator.targetImageUri == newImageUri
        assert Util.checkUrlExists(creator.targetImageUri)
        assert Util.checkUrlExists(creator.targetManifestUri)

        self.image = creator.targetImageUri
        self.oneUsername = self.username
        self.proxyOneadminPassword =  self.password
        self._runInstanceTest(cmdToRun='python -c "import dirq"')

        self._deleteImageAndManifestFromAppRepo(newImageUri)

    def _deleteImageAndManifestFromAppRepo(self, imageUri):
        urlDir = imageUri.rsplit('/',1)[0] + '/'

        curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.apprepoUsername,
                                                        self.apprepoPassword)]
        deleteUrlCmd = curlCmd + [ '-X', 'DELETE', urlDir]

        Util.execute(deleteUrlCmd,
                     verboseLevel=self.verboseLevel,
                     verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)

    def _createCreator(self, image):
        Util.generateSshKeyPair(self.sshKey)
        options = {}

        options['verboseLevel'] = self.verboseLevel

        options['author'] = 'Konstantin Skaburskas'
        options['comment'] = 'CentOS with python-dirq.'
        options['newImageGroupVersion'] = '1.99'
        options['newImageGroupName'] = 'base'
        options['newInstalledSoftwareName'] = 'CentOS'
        options['newInstalledSoftwareVersion'] = '5.5'
        options['excludeFromCreatedImage'] = '/etc/resolve.conf,/usr/sbin/pppdump'
        options['extraDiskSize'] = str(7*1024)
        options['scripts'] = '' # TODO: add some
        options['packages'] = 'python-dirq'
        options['extraOsReposUrls'] = 'http://download.fedora.redhat.com/pub/epel/5/i386/'

        options['installer'] = 'yum'
        options['os'] = 'centos'

        options['endpoint'] = getattr(self, 'endpoint')
        options['username'] = getattr(self, 'username', self.oneUsername)
        options['password'] = getattr(self, 'password', self.proxyOneadminPassword)

        options['apprepoEndpoint'] = self.apprepoEndpoint
        options['apprepoUsername'] = self.apprepoUsername
        options['apprepoPassword'] = self.apprepoPassword

        options['userPublicKeyFile'] = self.sshKeyPub
        options['userPrivateKeyFile'] = self.sshKey

        options['p12Certificate'] = self.p12Certificate
        options['p12Password'] = self.p12Password

        options['shutdownVm'] = True

        options['marketplaceEndpoint'] = Downloader.ENDPOINT
        
        configHolder = ConfigHolder(options)

        return Creator(image, configHolder)

    def marketPlaceTest(self):
        '''Place holder for marketplace test'''
        pass
    
    def claudiaTest(self):
        '''Cloudia test'''
        if self.claudiaCustomer:
            ClaudiaTest.ClaudiaTest.CLAUDIA_CUSTOMER = self.claudiaCustomer
        if self.claudiaServiceName:
            ClaudiaTest.ClaudiaTest.CLAUDIA_SERVICENAME = self.claudiaServiceName
        if self.claudiaOvfEndpoint:
            ClaudiaTest.ClaudiaTest.OVF = self.claudiaOvfEndpoint

        suite = self._createSuiteFromTestModule(ClaudiaTest)
        self._executeSuite(suite)

    def clusterTest(self):
        '''Cluster test'''
        ClusterTest.ClusterTest.sshKeyPub = self.sshKeyPub
        ClusterTest.ClusterTest.username = self.testUsername
        ClusterTest.ClusterTest.password = self.testPassword
        suite = self._createSuiteFromTestModule(ClusterTest)
        self._executeSuite(suite)
  
    def registrationTest(self):
        '''Registration test'''
        suite = self._createSuiteFromTestModule(RegistrationTest)
        self._executeSuite(suite)
  
    def _createSuiteFromTestModule(self, module):
        suite = unittest.TestSuite()
        tests = unittest.TestLoader().loadTestsFromModule(module)
        suite.addTests(tests)
        return suite
        
    def _executeSuite(self, suite):
        testResult = unittest.TextTestRunner(verbosity=2).run(suite)
        self.assertTrue(testResult.wasSuccessful())
