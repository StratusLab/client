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
import re
import os
from datetime import datetime
import time
import urllib2
import tempfile
import shutil

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Runner import Runner
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
from stratuslab.Util import sshCmdWithOutput
from stratuslab.Util import waitUntilPingOrTimeout
from stratuslab.Util import getHostnameFromUri
from stratuslab.Util import execute
import stratuslab.Util as Util
from Exceptions import ValidationException
from Exceptions import ExecutionException
from ManifestInfo import ManifestInfo
from ConfigParser import SafeConfigParser
from Authn import AuthnFactory
from stratuslab.system.ubuntu import installCmd as aptInstallCmd
from stratuslab.system.ubuntu import updateCmd as aptUpdateCmd
from stratuslab.system.ubuntu import cleanPackageCacheCmd as aptCleanPackageCacheCmd
from stratuslab.system.centos import installCmd as yumInstallCmd
from stratuslab.system.centos import updateCmd as yumUpdateCmd
from stratuslab.system.centos import cleanPackageCacheCmd as yumCleanPackageCacheCmd
from stratuslab.Uploader import Uploader
from stratuslab.Signator import Signator
from stratuslab.ManifestInfo import ManifestIdentifier
from stratuslab.Image import Image
from stratuslab.marketplace.Downloader import Downloader

VM_START_TIMEOUT = 60 * 10
VM_PING_TIMEPUT = 60 * 5

INSTALLERS = ('yum', 'apt') # TODO: should go to system/__init__.py

class Creator(object):

    _defaultChecksum = 'NOT CHECKSUMMED'
    checksums = {'md5'   :{'cmd':'md5sum',   'sum':_defaultChecksum},
                 'sha1'  :{'cmd':'sha1sum',  'sum':_defaultChecksum},
                 'sha256':{'cmd':'sha256sum','sum':_defaultChecksum},
                 'sha512':{'cmd':'sha512sum','sum':_defaultChecksum}}

    def __init__(self, image, configHolder):
        self.image = image
        self.configHolder = configHolder

        self.newImageGroupName = ''
        self.newInstalledSoftwareName = ''
        self.newInstalledSoftwareVersion = ''
        self.newImageGroupVersion = ''
        self.newImageGroupVersionWithManifestId = False
        self.author = ''
        self.comment = ''
        self.os = ''

        self.endpoint = ''
        self.apprepoEndpoint = ''

        self.extraOsReposUrls = ''
        self.packages = ''

        self.scripts = ''
        self.recipe = ''

        self.verboseLevel = ''

        self.shutdownVm = True

        self.signManifest = True

        self.options = Runner.defaultRunOptions()
        self.options.update(configHolder.options)
        self.configHolder.options.update(self.options)

        configHolder.assign(self)

        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')

        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.cloud.setEndpoint(self.endpoint)

        self.runner = None
        self.vmAddress = None
        self.vmId = None
        self.vmIp = None
        self.vmName = 'creator'

        # Structure of the repository
        self.appRepoStructure = 'images/#type_#/#os#-#osversion#-#arch#-#type#/#version#'
        # Repository image filename structure
        self.appRepoFilename = '#os#-#osversion#-#arch#-#type#-#version#.img.#compression#'

        self.userPublicKeyFile = self.options.get('userPublicKeyFile',
                                                  '%s/.ssh/id_rsa.pub' %
                                                    os.path.expanduser("~"))
        self.userPrivateKeyFile = self.userPublicKeyFile.strip('.pub')

        self.mainDisk = ''
        self.extraDisk = ''
        self.mountPointExtraDisk = '/media'
        self.imageFile = ''
        self.imageFileBundled = ''

        self.excludeFromBundle = ['/tmp/*',
                                  '/etc/ssh/ssh_host_*',
                                  '/root/.ssh/{authorized_keys,known_hosts}'
                                  ] + \
                                  self.options.get('excludeFromBundle','').split(',')

        self.installer = self.options.get('installer')

        self.targetImageUri = ''
        self.targetManifestUri = ''

        self.manifest = ''
        self.manifestObject = None
        self.newManifestFileName = None

        self.__listener = CreatorBaseListener()

    @staticmethod
    def checksumImageLocal(filename, chksums=ManifestInfo.MANDATORY_CHECKSUMS):
        # TODO: use 'hashlib' ?
        if not chksums:
            return {}

        import commands
        darwinChksumCmds = {'md5'   :'md5 -q',
                            'sha1'  :'shasum -a 1',
                            'sha256':'shasum -a 256',
                            'sha512':'shasum -a 512'}
        chksumCmds = {}
        for chksum in chksums:
            if commands.getoutput('uname') == 'Darwin':
                chksumCmds[chksum] = darwinChksumCmds[chksum]
            else:
                chksumCmds[chksum] = Creator.checksums[chksum]['cmd']

        chksumsResults = {}
        for chksum, cmd in chksumCmds.items():
            output = commands.getoutput(cmd + ' ' + filename)
            chksumsResults[chksum] = output.split(' ')[0]

        return chksumsResults

    def printDetail(self, msg):
        return Util.printDetail(msg, self.verboseLevel, Util.NORMAL_VERBOSE_LEVEL)

    def showName(self):

        self._updateAppRepoStructures()
        self._retrieveManifest()
        info = self._updateManifest()
        fileName = self.appRepoFilename

        self.printDetail('Building image name')

        fileName = self._buildRepoNameStructure(fileName, info)
        path = self._buildRepoNameStructure(self.appRepoStructure, info)
        return os.path.join(path, fileName)

    def _updateAppRepoStructures(self):
        self.printDetail('Retrieving Appliance Repository structure metadata')
        url = self._buildConfigFileUrl()
        config = None
        try:
            config = Util.wread(os.path.join(url, '.stratuslab/stratuslab.repo.cfg'))
        except urllib2.HTTPError:
            self._printError('Failed to reach url %s' % url)
        parser = SafeConfigParser()
        parser.readfp(config)
        self.appRepoStructure = parser.get('stratuslab_repo', 'repo_structure')
        self.appRepoFilename = parser.get('stratuslab_repo', 'repo_filename')

    def _buildConfigFileUrl(self):
        url = self.apprepoEndpoint or self._extractRootPath()
        self.printDetail('Using root url: %s' % url)
        return url

    def _extractRootPath(self):
        root = '/'.join(self.image.split('/')[:-4])
        return root

    def _buildRepoNameStructure(self, structure, info):
        return Uploader.buildRepoNameStructure(structure, info)

    def create(self):

        self._printAction('Starting image creation')

        try:
            self.buildAndStoreNodeIncrement()

            self._printAction('Image creation finished')
            print ' Image: %s' % self.targetImageUri
            print ' Manifest: %s' % self.targetManifestUri
            print '\n\tInstallation details can be found at: \n\t%s, %s' % (self.stdout.name,
                                                                            self.stderr.name)
        finally:
            self._shutdownNode()
        self._localCleanUp()

    def buildAndStoreNodeIncrement(self):
        self.startNode()
        self.buildNodeIncrement()
        self.storeNodeIncrement()

    def startNode(self):
        self._imageExists()

        self._retrieveManifest()
        self.__setAttributesFromManifest()

        self.__createRunner()

        self._startMachine()

        self._waitMachineNetworkUpOrAbort()

        self._checkIfCanConnectToMachine()

    def buildNodeIncrement(self):

        self._installPackages()
        self._executeScripts()
        self._executeRecipe()

        self._createImage()

        self._checksumImage()

        self._updateAndSaveManifest()
        self._signManifest()

        self._bundleImage()

    def storeNodeIncrement(self):
        self._uploadImageAndManifest()

    def _printAction(self, msg):
        Util.printAction(msg)
        self._notifyOnAction(msg)

    def _printStep(self, msg):
        Util.printStep(msg)
        self._notifyOnStep(msg)

    def _printError(self, msg):
        self._notifyOnError(msg)
        Util.printError(msg)

    def setListener(self, listener):
        if listener:
            self.__listener = listener

    def _notifyOnAction(self, note):
        self._notify('Action', note)

    def _notifyOnStep(self, note):
        self._notify('Step', note)

    def _notifyOnError(self, note):
        self._notify('Error', note)

    def _notify(self, operation, note):
        def callListener():
            notifyFunction = getattr(self.__listener, onOperation)
            notifyFunction(note)

        onOperation = 'on%s' % operation

        if hasattr(self.__listener, onOperation):
            pass
        elif hasattr(self.__listener, 'onAny'):
            onOperation = 'onAny'
        callListener()

    def _checkIfCanConnectToMachine(self):
        self._printStep('Check if we can connect to machine')

        cmd = 'true'
        try:
            self._sshCmdWithOutputVerb(cmd)
        except ExecutionException, e:
            sleepTime = 5
            maxCount = 2
            counter = 0
            while True:
                try:
                    self.printDetail('Sleeping %i sec. Retry %i out of %i.' % \
                                     (sleepTime, counter+1, maxCount))
                    time.sleep(sleepTime)
                    self._sshCmdWithOutputVerb(cmd)
                    break
                except ExecutionException, e:
                    if counter >= maxCount:
                        raise ExecutionException(e)
                    counter += 1

    def _imageExists(self):
        self._printStep('Checking that base image exists')
        self._checkImageExists()

    def _checkImageExists(self):
        imageObject = Image(self.configHolder)
        imageObject.checkImageExists(self.image)

    def __createRunner(self):
        self.configHolder.set('vmName', 
                              '%s: %s' % (self.vmName, Util.getTimeInIso8601()))
        self.configHolder.set('extraDiskSize', self._getExtraDiskSizeBasedOnManifest())
        self.configHolder.set('noCheckImageUrl', True)

        self.runner = Runner(self.image, self.configHolder)

    def _startMachine(self):
        self._printStep('Starting base image')

        try:
            self.vmId = self.runner.runInstance()[0]
        except Exception, msg:
            self._printError('An error occurred while starting machine: \n\t%s' % msg)
        try:
            _, self.vmIp = self.runner.getNetworkDetail(self.vmId)
            self.vmAddress = self.vmIp
        except Exception, e:
            self._printError('An error occurred while getting machine network details: \n\t%s' % str(e))

        self._printStep('Waiting for machine to boot')
        vmStarted = self.runner.waitUntilVmRunningOrTimeout(self.vmId,
                                                            VM_START_TIMEOUT)
        if not vmStarted:
            msg = 'Failed to start VM within %i seconds (id=%s, ip=%s)' % \
                                (VM_START_TIMEOUT, self.vmId, self.vmAddress)
            self.printDetail(msg)
            self._stopMachine()
            self._printError(msg)

    def _stopMachine(self):
        self._printStep('Shutting down machine')

        if self.vmId:
            # TODO: STRATUSLAB-414. This doesn't always work. Kill the machine instead.
            #self.cloud.vmStop(self.vmId)
            self.cloud.vmKill(self.vmId)
        else:
            Util.printWarning('Undefined VM ID, when trying to stop machine.')

    def _shutdownNode(self):
        if self.shutdownVm:
            self._stopMachine()
        else:
            self._printStep('Machine ready for your usage')
            print '\n\tMachine IP: %s' % self.vmIp
            print '\tRemember to stop the machine when finished'

    def _waitMachineNetworkUpOrAbort(self):
        self._printStep('Waiting for machine network to start')
        if not waitUntilPingOrTimeout(self.vmAddress, VM_PING_TIMEPUT):
            msg = 'Unable to ping VM in %i seconds (id=%s, ip=%s)' % \
                                    (VM_PING_TIMEPUT, self.vmId, self.vmAddress)
            self._printError(msg)
            self._stopMachine()

    def _getPublicAddress(self):
        return self.vmIp

    def _retrieveManifest(self):
        """Retrieve from marketplace as manifest object."""

        self._printStep('Retrieving image manifest')
        
        configHolder = self.configHolder.copy()
        
        downloader = Downloader(configHolder)
        downloader.downloadManifestByImageId(self.image)
        self.manifestObject = downloader.manifestObject
        self.manifest = self.manifestObject.tostring()

    def __setAttributesFromManifest(self):
        self._setOsFromManifest()
        self._setInstallerBasedOnOs()

    def _setOsFromManifest(self):
        # could have been set via command line parameter
        if not self.os:
            self.os = self._getAttrFromManifest('os').lower()

    def _getExtraDiskSizeBasedOnManifest(self):
        size = self._getAttrFromManifest('bytes')
        extra = 1024 ** 3 # extra 1 GB in bytes
        # NB! should be in MB
        newSize = str( (int(size) + extra) / (1024 * 1024) )
        return newSize

    def _getAttrFromManifest(self, attr):
#        info = ManifestInfo()
#        info.parseManifest(self.manifest)
        
        return getattr(self.manifestObject, attr)

    def _updateAndSaveManifest(self):
        self._printStep('Updating image manifest')

        self.manifestObject = self._updateManifest()

        self.manifest = self.manifestObject.tostring()

        self._saveManifest()

    def _updateManifest(self):
        self.printDetail('Updating manifest')
        info = ManifestInfo()

        info.parseManifest(self.manifest)
        for name, checksum in self.checksums.items():
            if not getattr(info, name):
                setattr(info, name, checksum['sum'])
        info.identifier = ManifestIdentifier().sha1ToIdentifier(info.sha1)
        info.created = Util.getTimeInIso8601()
        info.valid = Util.toTimeInIso8601(time.time() + ManifestInfo.IMAGE_VALIDITY)
        info.type = self.newImageGroupName or info.type
        info.os = self.newInstalledSoftwareName or info.os
        info.osversion = self.newInstalledSoftwareVersion or info.osversion
        info.user = self.author or info.user
        if self.newImageGroupVersionWithManifestId:
            # mangle version number for uniqueness
            if self.newImageGroupVersion:
                info.version = '%s.%s' % (self.newImageGroupVersion, info.identifier)
        else:
            info.version = self.newImageGroupVersion or info.version
        info.comment = self.comment or info.comment

        return info

    def _saveManifest(self):
        fd, self.manifestLocalFileName = tempfile.mkstemp('.xml')
        self.printDetail('Writing manifest to local temporary file: %s' % self.manifestLocalFileName)
        os.write(fd, self.manifest)
        os.close(fd)

    def _signManifest(self):
        if not self.signManifest:
            return
        self._printStep('Signing image manifest')

        signator = Signator(self.manifestLocalFileName, self.configHolder)
        signator.sign()
        shutil.move(signator.outputManifestFile, self.manifestLocalFileName)

    def _installPackages(self):
        self._printStep('Installing user packages')

        if len(self.packages) == 0:
            self.printDetail('No packages to install')
            return

        self._setUpExtraRepositories()

        self.printDetail('Installing packages: %s' % self.packages)

        ret = self._doInstallPackagesRemotly(self.packages)

        if ret != 0:
            self._printError('An error occurred while installing packages')

    def _setInstallerBasedOnOs(self):
        if self.os == 'centos':
            self.installer = 'yum'
        elif self.os == 'ubuntu':
            self.installer = 'apt'

    def _setUpExtraRepositories(self):
        if not self.extraOsReposUrls:
            return

        self.printDetail('Adding extra repositories')

        if self.installer not in INSTALLERS:
            ValidationException('Unknown installer %s. Bailing out.' %
                                self.installer)

        extraReposList = self.extraOsReposUrls.split(',')

        if self.installer == 'yum':
            for i,repoUrl in enumerate(extraReposList):
                repoName = getHostnameFromUri(repoUrl)
                cmd = """cat >> /etc/yum.repos.d/%(name)s.repo << EOF
[%(name)s]
name=%(name)s
baseurl=%(url)s
gpgcheck=0
enabled=1
EOF
""" % {'name' : '%s-%i'%(repoName,i), 'id': i, 'url' : repoUrl}
        elif self.installer == 'apt':
            for repoUrl in extraReposList:
                repoName = getHostnameFromUri(repoUrl)
                cmd = """cat >> /etc/apt/sourses.list.d/%(name)s.list
deb %(name)s
""" % {'name' : repoName}

        self._sshCmdWithOutput(cmd)

    def _doInstallPackagesRemotly(self, packages):
        cmd = self._buildInstallerCommand() + ' '
        cmd += ' '.join(packages.split(','))
        return self._sshCmd(cmd, stderr=self.stderr, stdout=self.stdout)

    def _buildInstallerCommand(self):
        if self.installer == 'yum':
            return yumInstallCmd
        elif self.installer == 'apt':
            return aptInstallCmd

    def _buildUpdaterCommand(self):
        if self.installer == 'yum':
            return yumUpdateCmd
        elif self.installer == 'apt':
            return aptUpdateCmd

    def _buildPackageCacheCleanerCommand(self):
        if self.installer == 'yum':
            return yumCleanPackageCacheCmd
        elif self.installer == 'apt':
            return aptCleanPackageCacheCmd

    def _executeScripts(self):
        self._printStep('Executing user scripts')

        if len(self.scripts) == 0:
            self.printDetail('No scripts to execute')
            return

        self._printStep('Executing scripts: ' % self.scripts)

        for script in self.scripts.split(','):
            scriptPath = '/tmp/%s' % os.path.basename(script)
            scp(script, 'root@%s:%s' % (self.vmAddress, scriptPath),
                self.userPrivateKeyFile, stderr=self.stderr, stdout=self.stdout)

            rc, output = self._sshCmdWithOutput(scriptPath, throwOnError=False)
            if rc != 0:
                self._printError('An error occurred while executing script %s:\n%s' % (script, output))

    def _executeRecipe(self):
        self._printStep('Executing user recipe')

        if len(self.recipe) == 0:
            self.printDetail('No scripts to execute')
            return

        fd, recipeFile = tempfile.mkstemp()
        try:
            os.write(fd, self.recipe)
            os.close(fd)
            os.chmod(recipeFile, 0755)
            scriptPath = '/tmp/%s' % os.path.basename(recipeFile)
            scp(recipeFile, 'root@%s:%s' % (self.vmAddress, scriptPath),
                self.userPrivateKeyFile, stderr=self.stderr, stdout=self.stdout)
    
            rc, output = self._sshCmdWithOutput(scriptPath, throwOnError=False)
            if rc != 0:
                self._printError('An error occurred while executing user recipe:\n%s' % output)
        finally:
            try:
                os.unlink(recipeFile)
            except:
                pass

    def _createImage(self):
        self._printStep('Creating image')

        self._setDiskNamesOfRemoteNode()

        extraDiskFirstPart = '%s1' % self.extraDisk
        extraDiskFirstPartMntPoint = '%s/%s' % (self.mountPointExtraDisk,
                                                extraDiskFirstPart)

        def umountAllPartitionsOfExtraDisk():
            cmd = 'for dev in /dev/%s*; do umount $dev; done' % self.extraDisk
            self._sshCmdWithOutput(cmd, throwOnError=False)

        def partitionExtraDisk():
            cmd = """sfdisk /dev/%s << EOF
;
EOF
""" % self.extraDisk
            self._sshCmdWithOutput(cmd)
        def makeFileSystemsOnExtraDisk():
            cmd = "mkfs.ext3 /dev/%s" % extraDiskFirstPart
            self._sshCmdWithOutput(cmd)

        def mountPartitionsFromExtraDisk():
            cmd = "mkdir -p %(mnt)s; mount /dev/%(ed1stPart)s %(mnt)s" % \
                    {'mnt' : extraDiskFirstPartMntPoint,
                     'ed1stPart': extraDiskFirstPart}
            self._sshCmdWithOutput(cmd)

        def stopServices():
            # don't stop those services
            runlevelOneSericesUp = ('sshd', 'network', 'iptables', 'ip6tables')

            cmd = 'ls -1 /etc/rc1.d/K*'
            _, services = self._sshCmdWithOutput(cmd)

            servicesToStop = []
            for s in services.split('\n'):
                if not re.search('(%s)$' % '|'.join(runlevelOneSericesUp), s):
                    servicesToStop.append(s)

            for srv in servicesToStop:
                if srv:
                    self._sshCmdWithOutput('%s stop' % srv, throwOnError=False)

        def doCleanupOnMainDisk():
            pkgCacheCleanCmd = self._buildPackageCacheCleanerCommand()
            self._sshCmdWithOutput(pkgCacheCleanCmd, throwOnError=False)

        def cloneMainDiskToRawImageFile():
            self.imageFile = '%s/%s.img' % (extraDiskFirstPartMntPoint,
                                            self.mainDisk)
            cmd = 'dd if=/dev/%(main)s of=%(image)s bs=$((64*1024))' % \
                    {'main'  : self.mainDisk,
                     'image' : self.imageFile}
            _, stat = self._sshCmdWithOutput(cmd)
            self.printDetail('Statistics on image creation:\n%s' % stat)

            self.imageFileBundled = '%s.gz' % self.imageFile

        def _removeFilesForExclusion(base=''):
            self._printStep('Removing files/directories to be excluded')

            filesOnBase = ['%s/%s' % (base, x) for x in self.excludeFromBundle if x]
            cmd = 'rm -rf %s' % ' '.join(filesOnBase).strip()

            self._sshCmd(cmd, throwOnError=False)

        def doCleanupOnImamge():
            imageFileMntDir = '%s.mntdir' % self.imageFile

            self._mountImageFirstLvmPart(imageFileMntDir)
            _removeFilesForExclusion(imageFileMntDir)
            self._umountOnRemote(imageFileMntDir)

        umountAllPartitionsOfExtraDisk()
        partitionExtraDisk()
        makeFileSystemsOnExtraDisk()
        mountPartitionsFromExtraDisk()
        stopServices()
        doCleanupOnMainDisk()
        cloneMainDiskToRawImageFile()
        doCleanupOnImamge()

    def _setDiskNamesOfRemoteNode(self):
        if self.os == 'centos':
            self.mainDisk  = 'hda'
            self.extraDisk = 'hdd'
        elif self.os == 'ubuntu':
            self.mainDisk  = 'sda'
            self.extraDisk = 'sdd'

    def _bundleImage(self):
        self._printStep('Bundling image')

        cmd = 'gzip -c %s > %s' % (self.imageFile, self.imageFileBundled)
        self._sshCmd(cmd)

    def _mountImageFirstLvmPart(self, imageFileMntDir):

        cmd = 'mkdir -p %s' % imageFileMntDir
        self._sshCmdWithOutput(cmd)

        # get start sector of LVM partition (ID: 8e)
        cmd = "fdisk -lu %(imageFile)s 2>/dev/null|grep 8e|awk '{print $2}'" % \
                {'imageFile': self.imageFile}
        _, offsetInSectors = self._sshCmdWithOutput(cmd)

        # offset to the first logical volume
        peStartSectors = 384
        peStartBytes = peStartSectors * 512
        offsetInBytes = '%i' % (int(offsetInSectors) * 512 + peStartBytes)

        # mount first logical volume
        cmd = "mount -o loop,offset=%(offset)s %(imageFile)s %(mntDir)s" % \
                {'offset'   : offsetInBytes,
                 'imageFile': self.imageFile,
                 'mntDir'   : imageFileMntDir}
        self._sshCmdWithOutput(cmd)

    def _umountOnRemote(self, dir):
        cmd = 'umount %s' % dir
        try:
            self._sshCmd(cmd, throwOnError=True)
        except ExecutionException:
            cmd = 'umount -lf %s' % dir
            self._sshCmdWithOutput(cmd)

    def _checksumImage(self):
        self._printStep('Checksumming image')

        self._checksumFile(self.imageFile)

    def _checksumFile(self, filename):
        for name, meta in self.checksums.items():
            checksumingCmd = '%s %s' % (meta['cmd'], filename)
            rc, output = self._sshCmdWithOutput(checksumingCmd, self.vmAddress)
            if rc != 0:
                raise ExecutionException('Could not get %s checksum for image:\n%s\n%s' %
                                         (name, checksumingCmd, output))
            self.checksums[name]['sum'] = output.split(' ')[0]

    def _sshCmd(self, cmd, throwOnError=True, **kwargs):
        ret = sshCmd(cmd, self.vmAddress,
                     sshKey=self.userPrivateKeyFile,
                     verboseLevel=self.verboseLevel,
                     verboseThreshold=Util.DETAILED_VERBOSE_LEVEL,
                     **kwargs)
        if ret and throwOnError:
            raise ExecutionException('Error executing command: %s' % cmd)
        return ret

    def _sshCmdWithOutput(self, cmd, throwOnError=True, **kwargs):
        rc, output = sshCmdWithOutput(cmd, self.vmAddress,
                                      sshKey=self.userPrivateKeyFile,
                                      verboseLevel=self.verboseLevel,
                                      verboseThreshold=Util.DETAILED_VERBOSE_LEVEL,
                                      **kwargs)
        if rc and throwOnError:
            raise ExecutionException('Error executing command: %s\n%s' % (cmd, output))
        return rc, output

    def _sshCmdWithOutputVerb(self, cmd, **kwargs):
        return self._sshCmdWithOutput(cmd, sshVerb=True, **kwargs)

    def _uploadImageAndManifest(self):
        self._printStep('Uploading image and manifest to appliance repository')

        if self.options.get('noUpload', False):
            self._printStep('Asked not to upload image to appliance repository')
            return

        self._doInstallPackagesRemotly('curl')

        self.configHolder.options['remoteImage'] = True
        self.configHolder.options['uploadOption'] = ''
        uploader = Uploader(self.manifestLocalFileName, self.configHolder)
        uploader.remoteServerAddress = self.vmAddress

        self.targetImageUri, self.targetManifestUri = \
            self._constructRemoteImageAndManifestUris()

        self._printStep('Uploading appliance\n')
        uploader.uploadFileFromRemoteServer(self.imageFileBundled, self.targetImageUri)

        self._printStep('Uploading manifest')
        uploader.uploadFile(self.manifestLocalFileName, self.targetManifestUri)

    def _constructRemoteImageAndManifestUris(self):
        image, manifest = self._constructRemoteImageAndManifestFileNames()
        return '%s/%s' % (self.apprepoEndpoint, image), \
                '%s/%s' % (self.apprepoEndpoint, manifest)

    def _constructRemoteImageAndManifestFileNames(self):
        imageName = self._constructRemoteImageName()
        nameBase = imageName.rsplit('.',2)[0] # remove .img.gz
        manifestName = '%s.xml' % nameBase
        return imageName, manifestName

    def _constructRemoteImageName(self):
        fileName = self._buildRepoNameStructure(self.appRepoFilename, self.manifestObject)
        path = self._buildRepoNameStructure(self.appRepoStructure, self.manifestObject)
        return os.path.join(path, fileName)

    def _localCleanUp(self):
        execute(['rm', '-rf', self.manifestLocalFileName])

    def getNewImageId(self):
        # FIXME: return ID when manifest gets uploaded to Marketplace
        return self.targetManifestUri
        #return self.manifestObject.identifier

class CreatorBaseListener(object):

    def __init__(self, verbose=False):
        if verbose:
            self.write = self.__beVerbose

    def write(self, msg):
        pass

    def __beVerbose(self, msg):
        print msg

    def onAction(self, msg):
        self.write('action: %s' % msg)

    def onStep(self, msg):
        self.write('step: %s' % msg)

    def onError(self, msg):
        self.write('error: %s' % msg)

