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
import re
import sys

from stratuslab.Monitor import Monitor
from stratuslab.Registrar import Registrar
from stratuslab.Runner import Runner
from stratuslab.Uploader import Uploader
from stratuslab.Creator import Creator
from stratuslab.Exceptions import NetworkException, OneException,\
    ClientException
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Exceptions import ExecutionException
from stratuslab.Exceptions import InputException
from stratuslab.ConfigHolder import ConfigHolder
import Util
from stratuslab.marketplace.Downloader import Downloader
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
import stratuslab.ClaudiaTest as ClaudiaTest
import stratuslab.ClusterTest as ClusterTest
import stratuslab.MonitoringTest as MonitoringTest
import stratuslab.RegistrationTest as RegistrationTest
import stratuslab.LdapAuthenticationTest as LdapAuthenticationTest
from stratuslab.PersistentDisk import PersistentDisk
from stratuslab.Util import sleep, printStep
from stratuslab.Image import Image
import tempfile

VM_START_TIMEOUT = 5 * 60 # 5 min

class Testor(unittest.TestCase):

    configHolder = None
    testNames = []

    def setUp(self):
        self.vmIds = []
        self.image = 'PvitUfM-uW2yWakWUNmd-TSPOiy'
        self.ubuntuImg = 'BXSSv_2udGkpKgi6fcCaVniz1Zd'
        self._unlinkFiles([self.sshKey, self.sshKeyPub])

    def tearDown(self):
        self._unlinkFiles([self.sshKey, self.sshKeyPub])

    def _unlinkFiles(self, filesList):
        for f in filesList:
            try:
                os.unlink(f)
            except: pass

    def __init__(self, methodName='dummy'):
        super(Testor, self).__init__(methodName)

        self.vmIds = []
        self.sshKey = '/tmp/id_rsa_smoke_test' + str(os.getpid())
        self.sshKeyPub = self.sshKey + '.pub'
        self.testsToRun = []
        self.quotaCpu = 2
        self.runner = None
        self.imageIdCreateImage = ''

        Testor.configHolder.assign(self)
        self._setFieldsFromEnvVars()

    def _setFieldsFromEnvVars(self):
        self._setSingleFieldFromEnvVar('apprepoUsername', 'STRATUSLAB_APPREPO_USERNAME')
        self._setSingleFieldFromEnvVar('apprepoPassword', 'STRATUSLAB_APPREPO_PASSWORD')
        self._setSingleFieldFromEnvVar('apprepoEndpoint', 'STRATUSLAB_APPREPO_ENDPOINT')
        self._setSingleFieldFromEnvVar('requestedIpAddress', 'STRATUSLAB_REQUESTED_IP_ADDRESS')
        self._setSingleFieldFromEnvVar('p12Certificate', 'STRATUSLAB_P12_CERTIFICATE')
        self._setSingleFieldFromEnvVar('p12Password', 'STRATUSLAB_P12_PASSWORD')
        self._setSingleFieldFromEnvVar('pdiskEndpoint', 'STRATUSLAB_PDISK_ENDPOINT')
        self._exportEndpointIfNotInEnv()
        self._setSingleFieldFromEnvVar('endpoint', 'STRATUSLAB_ENDPOINT')

    def _setSingleFieldFromEnvVar(self, field, env):
        if env in os.environ:
            setattr(self, field, os.environ[env])

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
                                cmdToRun=['ping -c 2 www.google.com'])

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
            self._startVm(instanceNumber=int(self.quotaCpu) + 1)
        except OneException, ex:
            message = "CPU quota exceeded (Quota: %s.0, Used: %s.0, Requested: 1.0)." % (self.quotaCpu, self.quotaCpu)
            self.assertTrue(message in ex.message, 'Quota not working, got %s expected %s' % (ex.message, message))
        else:
            self.fail('Quota not enforced')
        finally:
            self._createRunner().killInstances(self.runner.vmIds)
        
    def _excludeTests(self, tests):
        if self.testsToExclude:
            for test in self.testsToExclude.split(','):
                try:
                    tests.remove(test)
                except ValueError:
                    print "WARNING: Test '%s' not in a list of defined tests." % test

    def _runInstanceTest(self, withLocalNetwork=False, cmdToRun=['/bin/true'], msgRecipients=None):
        runner = self._startVm(withLocalNetwork=withLocalNetwork, msgRecipients=msgRecipients)
        self._repeatCall(self._ping, runner)
        for cmd in cmdToRun:
            self._repeatCall(self._loginViaSsh, runner, cmd)
        self._stopVm(runner)

    def _prepareLog(self, logFile):
        log = open(logFile, 'aw')
        log.write('\n' * 3 + '=' * 60 + '\n')
        log.write(str(datetime.datetime.now()) + '\n')
        log.write('=' * 60 + '\n' * 3)
        return log

    def _startVm(self, withLocalNetwork=False, requestedIpAddress=None, 
                 instanceNumber=1, noCheckImageUrl=False, msgRecipients=None,
                 raiseOnFailed=True):
        self.runner = self._createRunner(withLocalNetwork, requestedIpAddress)
        self.runner.instanceNumber = instanceNumber

        self.runner.noCheckImageUrl = noCheckImageUrl

        if not msgRecipients:
            self.runner.msgRecipients = msgRecipients

        vmIds = self.runner.runInstance()
        self.vmIds.extend(vmIds)

        for id in vmIds:
            vmStarted = self.runner.waitUntilVmRunningOrTimeout(id, VM_START_TIMEOUT,
                                                                failOn=('Failed'))
            if not vmStarted and raiseOnFailed:
                error = 'Failed to start VM id: %s' % id
                Util.printError(error, exit=False)
                raise OneException(error)

        return self.runner

    def _createRunner(self, withLocalNetwork=False, requestedIpAddress=None, persistentDiskUUID=None, image=None):
        Util.generateSshKeyPair(self.sshKey)

        if not image:
            image = self.image

        options = Runner.defaultRunOptions()
        options['username'] = self.testUsername
        options['password'] = self.testPassword
        options['userPublicKeyFile'] = self.sshKeyPub
        options['verboseLevel'] = self.verboseLevel
        options['specificAddressRequest'] = requestedIpAddress
        options['persistentDiskUUID'] = persistentDiskUUID
        options['pdiskEndpoint'] = self.pdiskEndpoint

        if withLocalNetwork:
            options['isLocalIp'] = True

        configHolder = ConfigHolder(options)
        return Runner(image, configHolder)

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
            res = Util.sshCmd(cmd, ip, sshKey=self.sshKey)
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
        configHolder.set('apprepoEndpoint', self.apprepoEndpoint)
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


    def notificationTest(self):
        '''Check notifications on VM state changes'''
        pass

        #notifier = NotificationUseCaseTest()

        #connection = None
        #channel = None

        #try:

        #    connection, channel = notifier.initializeMessageQueue()

        #    msgRecipients = notifier.createMsgRecipients()

        #    self._runInstanceTest(msgRecipients=msgRecipients)

        #    vmId = self.vmIds[0]

        #    notifier.checkNotificationMessages(connection, vmId)

        #finally:                
        #    notifier.cleanUpMessageQueue(connection)


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

    def createImageV1Test(self):
        '''Create a machine image based on a given one. Old version v1.'''
        self._doCreateImageV1()

    def _doCreateImageV1(self):
        creator = self._createCreator(self.imageIdCreateImage, v1=True)

        newImage = creator.showName()
        newImageUri = '%s/%s' % (creator.apprepoEndpoint, newImage)

        self._deleteImageAndManifestFromAppRepo(newImageUri)

        try:
            creator.create()
        except Exception, e:
            try:
                creator._stopMachine()
            except:
                pass
            raise e

        assert creator.targetImageUri == newImageUri
        assert Util.checkUrlExists(creator.targetImageUri)
        assert Util.checkUrlExists(creator.targetManifestUri)

        self.image = creator.targetImageUri
        self.oneUsername = self.username
        self.proxyOneadminPassword = self.password
        self._runInstanceTest(cmdToRun=['python -c "import dirq"'])

        self._deleteImageAndManifestFromAppRepo(newImageUri)

    def createImageTest(self):
        '''Create a machine image based on a given one.'''
        self._doCreateImage()

    def _doCreateImage(self):

        remote_test_file = '$HOME/createImageTest-%s' % str(os.getpid())
        script = """#!/bin/sh
touch %s
""" % remote_test_file

        fd, script_file = tempfile.mkstemp('.sh', 'script')
        os.write(fd, script)
        os.close(fd)

        creator = self._createCreator(self.imageIdCreateImage,
                                      script_file=script_file)

        try:
            creator.create()
        except Exception, e:
            try:
                creator._stopMachine()
            except:
                pass
            raise e
        finally:
            os.unlink(script_file)

        timeout = 1000
        t_stop = time.time() + timeout
        t_step  = 10
        print "Waiting %i sec for image bundling. One dot %i sec." % (timeout,
                                                                      t_step)
        while time.time() < t_stop:
            if creator.getVmState() in ('Done', 'Failed'):
                print
                break
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(t_step)

        # Assert instance state
        vm_state = creator.getVmState()
        if vm_state != 'Done':
            self.configHolder.username = self.testUsername
            self.configHolder.password = self.testPassword
            self.configHolder.endpoint = self.endpoint
            monitor = Monitor(self.configHolder)
            info = monitor._vmDetail(creator.getVmId())
            info_attributes = info.getAttributes()
            msg = "Image creation failed. Instance final state '%s'. Error: %s" % \
                        (vm_state, info_attributes.get('template_error_message',
                                                       'not set'))
            self.fail(msg)
        
        # Assert new image. 
        # Assuming we are running on FE and can access VM log file.
        vm_id = creator.getVmId()
        mp_and_id = ''
        for line in open('/var/log/one/%s.log' % vm_id).readlines():
            if re.search('MARKETPLACE_AND_IMAGEID', line):
                mp_and_id = line.split()
                break
        image_id = mp_and_id[-1].strip('\'')
        if not Image.isImageId(image_id):
            self.fail("Failed to obtain new image ID.")
        marketplace_url = mp_and_id[-2].strip('\'')
        if not Util.isValidNetLocation(marketplace_url):
            self.fail("Failed to get marketplace endpoint.") 

        self.configHolder.marketplaceEndpoint = marketplace_url
        ManifestDownloader(self.configHolder).getManifestInfo(image_id)

        self.image = image_id
        self.oneUsername = self.testUsername
        self.proxyOneadminPassword = self.testPassword
        cmds = ['python -c "import dirq"',
                'ls -l %s' % remote_test_file]
        self._runInstanceTest(cmdToRun=cmds)

    def _deleteImageAndManifestFromAppRepo(self, imageUri):
        urlDir = imageUri.rsplit('/', 1)[0] + '/'

        curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.apprepoUsername,
                                                        self.apprepoPassword)]
        deleteUrlCmd = curlCmd + [ '-X', 'DELETE', urlDir]

        Util.execute(deleteUrlCmd,
                     verboseLevel=self.verboseLevel,
                     verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)

    def _createCreator(self, image, v1=False, script_file=''):
        'For both new and old "v1" versions.'

        Util.generateSshKeyPair(self.sshKey)
        options = {}

        options['v1'] = v1
        
        if not v1:
            options['authorEmail'] = 'konstan@sixsq.com'
            options['saveDisk'] = True
        if v1:
            options['extraDiskSize'] = str(7 * 1024)
            options['apprepoEndpoint'] = self.apprepoEndpoint
            options['apprepoUsername'] = self.apprepoUsername
            options['apprepoPassword'] = self.apprepoPassword
            options['p12Certificate'] = self.p12Certificate
            options['p12Password'] = self.p12Password
    
        options['instanceType'] = 'c1.medium'
    
        options['verboseLevel'] = self.verboseLevel

        options['author'] = 'Konstantin Skaburskas'
        options['comment'] = 'Image with python-dirq.'
        options['newImageGroupVersion'] = '1.99'
        options['newImageGroupName'] = 'base'
        options['newInstalledSoftwareName'] = 'Linux'
        options['newInstalledSoftwareVersion'] = '0.0'
        options['excludeFromCreatedImage'] = '/etc/resolve.conf,/usr/sbin/pppdump'
        options['scripts'] = script_file
        options['packages'] = 'python-dirq'
        # python-dirq is in Fedora base repo
        #options['extraOsReposUrls'] = 'http://download.fedora.redhat.com/pub/epel/5/i386/'

        options['installer'] = 'yum'
        options['os'] = 'linux'

        options['endpoint'] = self.endpoint
        options['username'] = self.testUsername
        options['password'] = self.testPassword

        options['userPublicKeyFile'] = self.sshKeyPub
        options['userPrivateKeyFile'] = self.sshKey

        options['shutdownVm'] = True

        options['marketplaceEndpoint'] = Downloader.ENDPOINT
        
        configHolder = ConfigHolder(options)

        return Creator(image, configHolder)

    def webMonitorTest(self):
        '''Web Monitor test'''
        
        if not self.webMonitorHost:
            self.webMonitorHost = self.frontendIp

        uri = 'http://%s/cgi-bin' % self.webMonitorHost
        pages = ['nodelist.py', 'nodedetail.py', 'vmlist.py', 'vmdetail.py']

        for page in pages:
            url = uri + '/' + page  
            try:
                urllib2.urlopen(url, timeout=5)
            except Exception, ex:
                self.fail("Failed to open %s.\n%s" % (url, ex))

    def oneReportsErrorViaXmlRpcTest(self):
        '''Test if ONE reports error messages via XML RPC'''
        
        # invalid image
        self.image += '.gz'

        info, vmId = self._startStopVmAndGetVmInfo()

        try:
            errorMessage = info.attribs['template_error_message']
        except KeyError:
            self.fail("No error message set.")
        else:
            self.failUnless(errorMessage, "Empty error message.")
            print 'VM %s failed with error message:\n%s' % (vmId, errorMessage)
    
    def errorMessageInWebMonitorTest(self):
        '''Check if VM creation error message is on Web Monitor's VM details page'''

        # invalid image
        self.image += '.invalid'

        info, vmId = self._startStopVmAndGetVmInfo()

        try:
            errorMessage = info.attribs['template_error_message']
        except KeyError:
            self.fail("No error message set.")
        else:
            self.failUnless(errorMessage, "Empty error message.")
            if self.verboseLevel > 1:
                print 'VM %s failed with error message:\n%s' % (vmId, errorMessage)

        # check VM details page of Web Monitor
        if not self.webMonitorHost:
            self.webMonitorHost = self.endpoint

        url = 'http://%s/cgi-bin/vmdetail.py?id=%s' % (self.webMonitorHost, vmId)

        fh = urllib2.urlopen(url, timeout=5)
        page = fh.read()

        for line in errorMessage.replace('\\n', '\n').split('\n'):
            self.failUnless(line in page,
                            "Line '%s' of error message '%s' for VM %s wasn't found at %s" %
                            (line, errorMessage, vmId, url))

    def _startStopVmAndGetVmInfo(self):
        'Return VM monitoring info and VM id.'
        
        self._startVm(noCheckImageUrl=True, raiseOnFailed=False)
        vmId = self.runner.vmIds[0]
        self._stopVm(self.runner)

        options = {}
        options['endpoint'] = getattr(self, 'endpoint')
        options['username'] = getattr(self, 'username', self.oneUsername)
        options['password'] = getattr(self, 'password', self.proxyOneadminPassword)

        monitor = Monitor(ConfigHolder(options))
        info = monitor._vmDetail(vmId)

        return info, vmId

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
        
    def monitoringTest(self):
        '''Monitoring solution tests'''
        try:
            fh=open("/tmp/monitoring_test", "w+")
            fh.write("Empezado el fichero de texto\n"
                     "Esto esta empezando a rular!")
            fh.close()
        
            suite = self._createSuiteFromTestModule(MonitoringTest)
                                                    
            self._executeSuite(suite)    
                    
        except:
            pass
       
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
  
    def ldapAuthenticationTest(self):
        '''LDAP authentication test'''
        suite = self._createSuiteFromTestModule(LdapAuthenticationTest)
        self._executeSuite(suite)
  
    def _createSuiteFromTestModule(self, module):
        suite = unittest.TestSuite()
        tests = unittest.TestLoader().loadTestsFromModule(module)
        suite.addTests(tests)
        return suite
        
    def _executeSuite(self, suite):
        testResult = unittest.TextTestRunner(verbosity=2).run(suite)
        self.assertTrue(testResult.wasSuccessful())
        
    def persistentDiskStorageTest(self):
        '''Ensure that a disk can be created, written, stored and removed'''
        
        pdiskDevice = '/dev/hdc' # !!!! Configured for the default image (ttylinux)
        pdiskMountPoint = '/mnt/pdisk-test'
        testFile = '%s/pdisk.txt' % pdiskMountPoint
        testFileCmp = '/tmp/pdisk.cmp'
        testString = 'pdiskTest'
        
        configHolder = Testor.configHolder.copy()
        configHolder.pdiskUsername = Testor.configHolder.testUsername
        configHolder.pdiskPassword = Testor.configHolder.testPassword
        pdisk = PersistentDisk(configHolder)
        
        Util.printAction('Creating a new persistent disk')
        diskUUID = pdisk.createVolume(1, 'test %s' % datetime.datetime.today(), False)
        
        Util.printAction('Checking persistent disk exists')
        if not pdisk.volumeExists(diskUUID):
            self.fail('An error occurred while creating a persistent disk')
            
        Util.printAction('Getting number of available users (before)')
        availableUserBeforeStart, _ = pdisk.getVolumeUsers(diskUUID)
        Util.printAction('Starting machine with persistent disk')
        runner = self._startVmWithPDiskAndWaitUntilUp(diskUUID)
        Util.printAction('Getting number of available users (after)')
        availableUserAfterStart, _ = pdisk.getVolumeUsers(diskUUID)
        
        if availableUserAfterStart != (availableUserBeforeStart-1):
            self.fail('Available users on persistent disk have to decrease by '
                      'one (%s, %s)' % 
                      (availableUserBeforeStart, availableUserAfterStart))
    
        self._formatDisk(runner, pdiskDevice)
        self._mountDisk(runner, pdiskDevice, pdiskMountPoint)
        self._writeToFile(runner, testFile, testString)
        self._umountPDiskAndStopVm(runner, pdiskDevice)

        availableUserAfterStop, _ = pdisk.getVolumeUsers(diskUUID)
        
        if availableUserAfterStop != availableUserBeforeStart:
            self.fail('Available users on persistent disk have to be the same '
                      'as when VM has started')
    
        runner = self._startVmWithPDiskAndWaitUntilUp(diskUUID)
        self._mountDisk(runner, pdiskDevice, pdiskMountPoint)
        self._writeToFile(runner, testFileCmp, testString)
        self._compareFiles(runner, testFile, testFileCmp)
        self._umountPDiskAndStopVm(runner, pdiskDevice)      
        
        availableUserAfterStop, _ = pdisk.getVolumeUsers(diskUUID)
        
        if availableUserAfterStop != availableUserBeforeStart:
            self.fail('Available users on persistent disk have to be the same '
                      'as when VM has started')

        Util.printAction('Removing persistent disk...')
        pdisk.deleteVolume(diskUUID)
        
        try:
            if pdisk.volumeExists(diskUUID):
                self.fail('The persistent disk %s is still present' % diskUUID)
        except ClientException, ex:
            if not re.match('404', ex.status):
                self.fail('The persistent disk %s is still present' % diskUUID)
            
    def persistentDiskStorageHotplugTest(self):
        '''Ensure that a disk hot-plugged to a VM and then hot-unplugged'''
        
        pdiskDevice = '/dev/%s'
        pdiskMountPoint = '/mnt/pdisk-test'
        testFile = '%s/pdisk.txt' % pdiskMountPoint
        testFileCmp = '/tmp/pdisk.cmp'
        testString = 'pdiskTest'
        
        configHolder = Testor.configHolder.copy()
        configHolder.pdiskUsername = Testor.configHolder.testUsername
        configHolder.pdiskPassword = Testor.configHolder.testPassword
        pdisk = PersistentDisk(configHolder)
        
        runner = self._startVmWithPDiskAndWaitUntilUp(image=self.ubuntuImg)
        
        Util.printAction('Creating a new persistent disk')
        diskUUID = pdisk.createVolume(1, 'test %s' % datetime.datetime.today(),
                                      False)
        
        Util.printAction('Checking persistent disk exists')
        if not pdisk.volumeExists(diskUUID):
            self.fail('An error occurred while creating a persistent disk')
        
        self._modeprobe(runner, 'acpiphp')
        vmId = self.vmIds[0]
        node = runner.cloud.getVmNode(vmId)
        
        printStep('Attaching pdisk to VM')
        
        availableUserBeforeAttach, _ = pdisk.getVolumeUsers(diskUUID)
        device = pdisk.hotAttach(node, vmId, diskUUID)
        availableUserAfterAttach, _ = pdisk.getVolumeUsers(diskUUID)
        
        if availableUserAfterAttach != (availableUserBeforeAttach-1):
            self.fail('Available users on persistent disk have to decrease by '
                      'one; before=%s, after=%s' % 
                      (availableUserBeforeAttach, availableUserAfterAttach))
        
        self._formatDisk(runner, pdiskDevice % device)
        self._mountDisk(runner, pdiskDevice % device, pdiskMountPoint)
        self._writeToFile(runner, testFile, testString)
        self._umountDisk(runner, pdiskDevice % device)
        
        printStep('Detaching pdisk of VM')
        pdisk.hotDetach(node, vmId, diskUUID)

        availableUserAfterDetach, _ = pdisk.getVolumeUsers(diskUUID)
        
        if availableUserAfterDetach != availableUserBeforeAttach:
            self.fail('Available users on persistent disk have to be the '
                      'same as when VM has started; before=%s, after=%s' %
                      (availableUserBeforeAttach, availableUserAfterDetach))
        
        printStep('Re-attaching pdisk to VM')
        device = pdisk.hotAttach(node, vmId, diskUUID)
        
        self._mountDisk(runner, pdiskDevice % device, pdiskMountPoint)
        self._writeToFile(runner, testFileCmp, testString)
        self._compareFiles(runner, testFile, testFileCmp)
        self._umountPDiskAndStopVm(runner, pdiskDevice % device)
        
        availableUserAfterStop, _ = pdisk.getVolumeUsers(diskUUID)
        
        if availableUserAfterStop != availableUserBeforeAttach:
            self.fail('Available users on persistent disk have to be the '
                      'same as when VM has started; before=%s, after=%s' % 
                      (availableUserBeforeAttach, availableUserAfterStop))

        Util.printAction('Removing persistent disk...')
        pdisk.deleteVolume(diskUUID)
            
        try:
            if pdisk.volumeExists(diskUUID):
                self.fail('The persistent disk %s is still present' % diskUUID)
        except ClientException, ex:
            if not re.match('404', ex.status):
                self.fail('The persistent disk %s is still present' % diskUUID)
        
    def _startVmWithPDiskAndWaitUntilUp(self, pdisk=None, image=None):
        runner = self._createRunner(persistentDiskUUID=pdisk, image=image)
        vmIds = runner.runInstance()
        if len(vmIds) < 1:
            self.fail('An error occurred while starting a VM')
        if not runner.waitUntilVmRunningOrTimeout(vmIds[0], failOn=('Failed')):
            self.fail('Failed starting VM: image %s, pdisk %s' % (str(image),
                                                                  str(pdisk)))
        self.vmIds.extend(vmIds)
        self._repeatCall(self._ping, runner)
        self._repeatCall(self._loginViaSsh, runner, '/bin/true')
        return runner
    
    def _umountPDiskAndStopVm(self, runner, pdiskDevice):
        self._umountDisk(runner, pdiskDevice)
        Util.printStep('Stopping VM...')
        self._stopVm(runner)
        self.vmIds = []
        # Wait for the pdisk hook to be executed
        sleep(20)
    
    def _formatDisk(self, runner, device):
        Util.printStep('Formating device %s' % device)
        mkfsScript = '/tmp/mkfs'
        self._loginViaSsh(runner, 'echo "echo \'y\' | /sbin/mkfs.ext3 %s" > %s' 
                                    % (device, mkfsScript))
        self._loginViaSsh(runner, 'bash %s' % mkfsScript)
        
    def _mountDisk(self, runner, device, mountPoint):
        Util.printStep('Mounting device %s in %s...' % (device, mountPoint))
        self._loginViaSsh(runner, 'mkdir -p %s' % mountPoint)
        self._loginViaSsh(runner, 'mount %s %s' % (device, mountPoint))
    
    def _umountDisk(self, runner, device):
        Util.printStep('Unmounting device %s...' % device)
        self._loginViaSsh(runner, 'umount %s' % device)

    def _writeToFile(self, runner, filename, what):
        Util.printStep('Writing content to %s...' % filename)
        self._loginViaSsh(runner, 'echo "%s" > %s' % (what, filename))
        
    def _compareFiles(self, runner, file1, file2):
        Util.printStep('Comparing %s and %s content...' % (file1, file2))
        self._loginViaSsh(runner, 'diff %s %s' % (file1, file2))
        
    def _modeprobe(self, runner, module):
        Util.printStep('Loading module %s...' % module)
        self._loginViaSsh(runner, 'modprobe %s' % module)
        
    
