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
import re
import tempfile
from os.path import splitext
from os import mkdir, rmdir, remove

from stratuslab.Monitor import Monitor
from stratuslab.Registrar import Registrar
from stratuslab.marketplace.Uploader import Uploader as marketplaceUploader
from stratuslab.Creator import Creator
from stratuslab.Exceptions import OneException, ClientException
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Exceptions import ExecutionException
from stratuslab.Exceptions import InputException
from stratuslab.ConfigHolder import ConfigHolder
import Util
from stratuslab.marketplace.Downloader import Downloader
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
import stratuslab.ClusterTest as ClusterTest
import stratuslab.RegistrationTest as RegistrationTest
import stratuslab.LdapAuthenticationTest as LdapAuthenticationTest
from stratuslab.volume_manager.volume_manager_factory import VolumeManagerFactory
from stratuslab.vm_manager.vm_manager_factory import VmManagerFactory
from stratuslab.Util import sleep, filePutContent
from stratuslab.Util import printStep, printInfo, printWarning
from stratuslab.image.Image import Image
from stratuslab.ManifestInfo import ManifestInfo


VM_START_TIMEOUT = 5 * 60  # 5 min


class Testor(unittest.TestCase):
    configHolder = None
    testNames = []

    def setUp(self):
        self.vmIds = []
        self.image = 'BN1EEkPiBx87_uLj2-sdybSI-Xb'  # ttylinux v14 x86_64
        self.ubuntuImg = 'BXSSv_2udGkpKgi6fcCaVniz1Zd'
        self._unlinkFiles([self.sshKey, self.sshKeyPub])

    def tearDown(self):
        self._unlinkFiles([self.sshKey, self.sshKeyPub])

    def _unlinkFiles(self, filesList):
        for f in filesList:
            try:
                os.unlink(f)
            except:
                pass

    def __init__(self, methodName='dummy'):
        super(Testor, self).__init__(methodName)

        self.vmIds = []
        self.sshKey = '/tmp/id_rsa_smoke_test' + str(os.getpid())
        self.sshKeyPub = self.sshKey + '.pub'
        self.testsToRun = []
        self.quotaCpu = 2
        self.runner = None

        Testor.configHolder.assign(self)
        self._setFieldsFromEnvVars()

    def _setFieldsFromEnvVars(self):
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
            raise ConfigurationException(
                'Missing environment variable %s or configuration parameter frontend_ip' % Util.envEndpoint)
        os.environ[Util.envEndpoint] = self.frontendIp

    def dummy(self):
        pass

    def runTests(self):
        suite = unittest.TestSuite()
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
        """Start new instance, ping it via public network and ssh into it, then stop it."""
        self._runInstanceTest()

    def runInstanceLocalNetworkTest(self):
        """Start new instance, ping it via local network and ssh into it, then stop it."""
        self._runInstanceTest(withLocalNetwork=True,
                              cmdToRun=['ping -c 2 www.google.com'])

    def runInstanceRequestedNetworkTest(self):
        """Start new instance, ping it via requested IP address and ssh into it, then stop it."""

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
        """Start x instances, where x is the cpu quota +1, then stop them."""

        printInfo('Current cpu quota: %s, starting as many +1' % self.quotaCpu)
        try:
            self._startVm(instanceNumber=int(self.quotaCpu) + 1)
        except OneException, ex:
            message = "CPU quota exceeded (Quota: %s.0, Used: %s.0, Requested: 1.0)." % (self.quotaCpu, self.quotaCpu)
            self.assertTrue(message in str(ex), 'Quota not working, got %s expected %s' % (ex.message, message))
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
                    printWarning("WARNING: Test '%s' not in a list of defined tests." % test)

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

        for vmId in vmIds:
            vmStarted = self.runner.waitUntilVmRunningOrTimeout(vmId, VM_START_TIMEOUT,
                                                                failOn='Failed')
            if not vmStarted and raiseOnFailed:
                error = 'Failed to start VM id: %s' % vmId
                Util.printError(error, exit=False)
                raise OneException(error)

        return self.runner

    def _createRunner(self, withLocalNetwork=False, requestedIpAddress=None,
                      persistentDiskUUID=None, image=None):
        Util.generateSshKeyPair(self.sshKey)

        if not image:
            image = self.image

        options = VmManagerInstance.defaultRunOptions()
        options['username'] = self.testUsername
        options['password'] = self.testPassword
        options['userPublicKeyFile'] = self.sshKeyPub
        options['verboseLevel'] = self.verboseLevel
        options['specificAddressRequest'] = requestedIpAddress
        options['persistentDiskUUID'] = persistentDiskUUID
        options['pdiskEndpoint'] = self.pdiskEndpoint
        options['marketplaceEndpoint'] = self.marketplaceEndpoint

        if withLocalNetwork:
            options['isLocalIp'] = True

        configHolder = ConfigHolder(options)
        return VmManagerFactory.create(image, configHolder)

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

    def _checkAttributePresentAndInitialized(self, attrs):
        self._checkAttributePresent(attrs)
        self._checkAttributeInitialized(attrs)

    def _checkAttributePresent(self, attrs):
        for attr in attrs:
            if attr not in self.__dict__:
                raise Exception('Missing attribute %s. Missing an option argument?' % attr)

    def _checkAttributeInitialized(self, attrs):
        for attr in attrs:
            if not getattr(self, attr):
                raise Exception('Attribute %s is not set. Missing an option argument?' % attr)

    def _generateDummyImage(self, filename, size=2):
        devNull = open(os.path.devnull, 'w')
        Util.execute(['dd', 'if=/dev/zero', 'of=%s' % filename, 'bs=1000000', 'count=%s' % size],
                     stdout=devNull, stderr=devNull)
        devNull.close()

    def registrarTest(self):
        """Register a new node with ONE server, check that it is properly registered and remove it"""
        configHolder = self.configHolder.copy()
        configHolder.options['infoDriver'] = 'kvm'
        configHolder.options['virtDriver'] = 'kvm'
        configHolder.options['transfertDriver'] = 'nfs'
        configHolder.options['networkDriver'] = 'dummy'
        configHolder.options['username'] = self.oneUsername
        configHolder.options['password'] = self.proxyOneadminPassword
        registrar = Registrar(configHolder)
        hostname = 'registrar.ip.test'
        vmId = registrar.register([hostname])
        monitor = Monitor(configHolder)
        info = monitor.nodeDetail([vmId])[0]
        self.assertEqual(hostname, info.name)
        registrar.deregister(hostname)
        self.assertRaises(Exception, monitor.nodeDetail, [vmId])


    def formatAvailableTests(self):
        result = "Available tests:\n"
        for testName, testDoc in self._extractTestDescriptions():
            result += "    - %s: %s\n" % (testName, testDoc)
        return result

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
        """Create a machine image based on a given one."""

        self._checkAttributePresentAndInitialized(['imageIdCreateImage',
                                                   'authorEmailCreateImage'])
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
        t_step = 10
        printInfo("Waiting %i sec for image bundling." % timeout)

        while time.time() < t_stop:
            if creator.getVmState() in ('Done', 'Failed'):
                break
            printInfo('Time remaining: %d' % (t_stop - time.time()))
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

        self.marketplaceEndpoint = marketplace_url
        self._runInstanceTest(cmdToRun=cmds)

    def _createCreator(self, image, script_file=''):
        Util.generateSshKeyPair(self.sshKey)
        options = {}

        options['marketplaceEndpointNewimage'] = getattr(self, 'marketplaceEndpointUpload', '')

        options['authorEmail'] = self.authorEmailCreateImage
        options['saveDisk'] = True

        options['instanceType'] = 'c1.medium'

        options['verboseLevel'] = self.verboseLevel

        options['author'] = 'Jane Tester'
        options['comment'] = 'NB! Test image.'
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

    def _registerInvalidImageInMarketplace(self):
        manifest_file = Util.get_resources_file(['manifest-invalid-sha1.xml'])

        manifestInfo = ManifestInfo()
        manifestInfo.parseManifestFromFile(manifest_file)

        image_id = manifestInfo.identifier

        configHolder = ConfigHolder()
        configHolder.set('marketplaceEndpoint', self.marketplaceEndpoint)
        uploader = marketplaceUploader(configHolder)
        uploader.upload(manifest_file)

        return image_id

    def _startStopInvalidImage(self):
        mpendp_save = self.marketplaceEndpoint
        self.marketplaceEndpoint = self.marketplaceEndpointUpload or mpendp_save

        try:
            self.image = self._registerInvalidImageInMarketplace()
            info, vmId = self._startStopVmAndGetVmInfo()
        finally:
            self.marketplaceEndpoint = mpendp_save

        return info, vmId

    def oneReportsErrorViaXmlRpcTest(self):
        """Test if ONE reports error messages via XML RPC"""

        info, vmId = self._startStopInvalidImage()

        try:
            errorMessage = info.attribs['template_error_message']
        except KeyError:
            self.fail("No error message set.")
        else:
            self.failUnless(errorMessage, "Empty error message.")
            printInfo('VM %s failed with error message:\n%s' % (vmId, errorMessage))

    def _startStopVmAndGetVmInfo(self):
        """Return VM monitoring info and VM id."""

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
        """Placeholder for marketplace test"""
        pass

    def clusterTest(self):
        """Cluster test"""
        ClusterTest.ClusterTest.sshKeyPub = self.sshKeyPub
        ClusterTest.ClusterTest.username = self.testUsername
        ClusterTest.ClusterTest.password = self.testPassword
        suite = self._createSuiteFromTestModule(ClusterTest)
        self._executeSuite(suite)

    def registrationTest(self):
        """Registration test"""
        suite = self._createSuiteFromTestModule(RegistrationTest)
        self._executeSuite(suite)

    def ldapAuthenticationTest(self):
        """LDAP authentication test"""
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
        """Ensure that a disk can be created, written, stored and removed"""

        pdiskDevice = '/dev/hdc'  # !!!! Configured for the default image (ttylinux)
        pdiskMountPoint = '/mnt/pdisk-test'
        testFile = '%s/pdisk.txt' % pdiskMountPoint
        testFileCmp = '/tmp/pdisk.cmp'
        testString = 'pdiskTest'

        configHolder = Testor.configHolder.copy()
        configHolder.pdiskUsername = Testor.configHolder.testUsername
        configHolder.pdiskPassword = Testor.configHolder.testPassword
        pdisk = VolumeManagerFactory.create(configHolder)

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

        if availableUserAfterStart != (availableUserBeforeStart - 1):
            self.fail('Available users on persistent disk have to decrease by '
                      'one (%s, %s)' %
                      (availableUserBeforeStart, availableUserAfterStart))

        self._formatDisk(runner, pdiskDevice)
        self._mountDisk(runner, pdiskDevice, pdiskMountPoint)
        self._writeToFile(runner, testFile, testString)
        self._umountPDiskAndStopVm(runner, pdiskDevice)

        # Allow a few seconds for the disk to be dismounted.
        time.sleep(10)

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
        """Ensure that a disk hot-plugged to a VM and then hot-unplugged"""

        pdiskDevice = '/dev/%s'
        pdiskMountPoint = '/mnt/pdisk-test'
        testFile = '%s/pdisk.txt' % pdiskMountPoint
        testFileCmp = '/tmp/pdisk.cmp'
        testString = 'pdiskTest'

        configHolder = Testor.configHolder.copy()
        configHolder.pdiskUsername = Testor.configHolder.testUsername
        configHolder.pdiskPassword = Testor.configHolder.testPassword
        pdisk = VolumeManagerFactory.create(configHolder)

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

        if availableUserAfterAttach != (availableUserBeforeAttach - 1):
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

    def persistentDiskStorageDownloadTest(self):
        """Check that an image can be downloaded correctly"""
        pdiskDevice = '/dev/hdc'  # !!!! Configured for the default image (ttylinux)
        pdiskMountPoint = '/mnt/pdisk-test'
        testFile = '%s/pdisk.txt'
        testString = 'pdiskTest'
        downloadedCompressedDisk = '/var/tmp/pdisk-img.gz'
        localMountPoint = '/mnt/pdisk-check'
        localTestFile = '/tmp/pdiskGzip.tmp'

        configHolder = Testor.configHolder.copy()
        configHolder.pdiskUsername = Testor.configHolder.testUsername
        configHolder.pdiskPassword = Testor.configHolder.testPassword
        pdisk = VolumeManagerFactory.create(configHolder)

        Util.printAction('Creating a new persistent disk')
        diskUUID = pdisk.createVolume(1, 'test %s' % datetime.datetime.today(), False)

        Util.printAction('Checking persistent disk exists')
        if not pdisk.volumeExists(diskUUID):
            self.fail('An error occurred while creating a persistent disk')

        Util.printAction('Starting machine with persistent disk')
        runner = self._startVmWithPDiskAndWaitUntilUp(diskUUID)

        self._formatDisk(runner, pdiskDevice)
        self._mountDisk(runner, pdiskDevice, pdiskMountPoint)
        self._writeToFile(runner, testFile % pdiskMountPoint, testString)
        self._umountPDiskAndStopVm(runner, pdiskDevice)

        try:
            Util.printAction('Downloading volume...')
            # compressed disk comes in HTTP response - don't print it from HTTP client!
            verb_save = pdisk.client.verboseLevel
            pdisk.client.verboseLevel = 0
            pdisk.downloadVolume(diskUUID, downloadedCompressedDisk)
            pdisk.client.verboseLevel = verb_save
            volume = self._gunzip(downloadedCompressedDisk)
        finally:
            try:
                remove(downloadedCompressedDisk)
            except:
                pass

        try:
            if not self._localMount(volume, localMountPoint, ['loop', ]):
                self.fail('Error mounting downloaded image, corrupted?')

            filePutContent(localTestFile, testString)

            fileEquals = self._compareLocalFiles(localTestFile, testFile % localMountPoint)

            if not fileEquals:
                self.fail('Downloaded volume is corrupted')

            self._localUmount(localMountPoint)
        finally:
            Util.printAction('Post test clean-up...')
            try:
                remove(volume)
            except:
                pass
            try:
                rmdir(localMountPoint)
            except:
                pass

    def _startVmWithPDiskAndWaitUntilUp(self, pdisk=None, image=None):
        runner = self._createRunner(persistentDiskUUID=pdisk, image=image)
        vmIds = runner.runInstance()
        if len(vmIds) < 1:
            self.fail('An error occurred while starting a VM')
        if not runner.waitUntilVmRunningOrTimeout(vmIds[0], failOn='Failed'):
            self.fail('Failed starting VM: image %s, pdisk %s' % (str(image or runner.vm_image),
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

    def _localMount(self, device, mountPoint, options=[]):
        Util.printStep('Mounting device %s on %s with options %s' % (device, mountPoint,
                                                                     (', '.join(options) or '<no options>')))
        mountOptions = ['-o', ','.join(options)]
        try:
            mkdir(mountPoint)
        except:
            pass
        rc, output = Util.executeGetStatusOutput(['mount'] + mountOptions + [device, mountPoint],
                                                 verboseLevel=self.verboseLevel)
        if output:
            printInfo(output)
        return rc == 0 and True or False

    def _localUmount(self, device):
        Util.printStep('Unmounting device %s...' % device)
        Util.execute(['umount', device])

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

    def _compareLocalFiles(self, file1, file2):
        Util.printStep('Comparing %s and %s content...' % (file1, file2))
        return Util.execute(['diff', file1, file2])

    def _gunzip(self, filename):
        Util.printStep("Unzipping file %s..." % filename)
        rc, output = Util.execute(['/bin/gunzip', filename], withOutput=True)
        if rc != 0:
            raise ExecutionException('Failed unzipping file: %s' % output)
        return splitext(filename)[0]
