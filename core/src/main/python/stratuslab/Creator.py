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
import os
from datetime import datetime
import time
import urllib2
import tempfile

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Runner import Runner
from stratuslab.Util import sshCmd
from stratuslab.Util import sshCmdWithOutput
from stratuslab.Util import waitUntilPingOrTimeout
from stratuslab.Util import getHostnameFromUri
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
from stratuslab.ManifestInfo import ManifestIdentifier
from stratuslab.Image import Image
from stratuslab.system import Systems
from stratuslab import Defaults
from stratuslab.marketplace.ManifestDownloader import ManifestDownloader
from stratuslab.Monitor import Monitor

class Creator(object):

    VM_START_TIMEOUT = 60 * 10
    VM_PING_TIMEPUT = 60 * 5

    excludeFromCreatedImageDefault = ['/tmp/*',
                                      '/etc/ssh/ssh_host_*',
                                      '/root/.ssh/{authorized_keys,known_hosts}']

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
        self.authorEmail = ''
        self.marketplaceEndpointNewimage = ''

        self.endpoint = ''
        self.apprepoEndpoint = ''

        self.extraOsReposUrls = ''
        self.packages = ''

        self.scripts = ''
        self.prerecipe = ''
        self.recipe = ''

        self.verboseLevel = ''

        self.shutdownVm = True

        self.signManifest = True

        self.vmStartTimeout = self.VM_START_TIMEOUT
        self.vmPingTimeout = self.VM_PING_TIMEPUT

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
        self.appRepoStructure = '#type_#/#os#-#osversion#-#arch#-#type#/#version#'
        # Repository image filename structure
        self.appRepoFilename = '#os#-#osversion#-#arch#-#type#-#version#.img.#compression#'

        self.userPublicKeyFile = self.options.get('userPublicKeyFile',
                                                  Defaults.sshPublicKeyLocation)
        self.userPrivateKeyFile = self.userPublicKeyFile.strip('.pub')

        self.mainDisk = ''
        self.extraDisk = ''
        self.mountPointExtraDisk = '/media'
        self.imageFile = ''
        self.imageFileBundled = ''

        self.excludeFromCreatedImage = \
                                self.excludeFromCreatedImageDefault + \
                                self.options.get('excludeFromCreatedImage','').split(',')

        self.installer = self.options.get('installer')

        self.targetImageUri = ''
        self.targetManifestUri = ''

        self.manifest = ''
        self.manifestObject = None
        self.newManifestFileName = None

        self.manifestLocalFileName = ''

        self.__listener = CreatorBaseListener()

    def printDetail(self, msg):
        return Util.printDetail(msg, self.verboseLevel, Util.NORMAL_VERBOSE_LEVEL)

    def showName(self):

        def _updateManifestForNewImageNameInAppRepo(manifestInfo):
            manifestInfo.type = self.newImageGroupName or manifestInfo.type
            manifestInfo.version = self.newImageGroupVersion or manifestInfo.version
            manifestInfo.os = self.newInstalledSoftwareName or manifestInfo.os
            manifestInfo.osversion = self.newInstalledSoftwareVersion or manifestInfo.osversion
            return manifestInfo

        self._updateAppRepoStructures()
        self._retrieveManifest()
        info = self.manifestObject
        info = _updateManifestForNewImageNameInAppRepo(info)
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

        self.startNode()
        try:
            self.buildNodeIncrement()
            self._printAction('Finished building image increment.')
            self._printAction('Please check %s for new image ID and instruction.' %\
                              self.authorEmail)
        finally:
            self._shutdownNode()
        self._localCleanUp()

    def startNode(self):
        self._imageExists()

        self._retrieveManifest()
        self.__setAttributesFromManifest()

        self.__createRunner()

        self._startMachine()

        self._waitMachineNetworkUpOrAbort()

        self._checkIfCanConnectToMachine()

    def buildNodeIncrement(self):

        self._executePrerecipe()
        self._installPackages()
        self._executeRecipe()
        self._executeScripts()

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
        self._printStep('Check if we can connect to the machine')

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
        image = Image(self.configHolder)
        image.checkImageExists(self.image)

    def _getCreateImageTemplateDict(self):
        return {'CREATOR_EMAIL' : self.authorEmail,
                'CREATOR_NAME' : self.author,
                'NEWIMAGE_COMMENT' : self.comment,
                'NEWIMAGE_VERSION' : self.newImageGroupVersion,
                'NEWIMAGE_MARKETPLACE' : self.marketplaceEndpointNewimage }

    def __createRunner(self):
        self.configHolder.set('vmName', 
                              '%s: %s' % (self.vmName, Util.getTimeInIso8601()))
        self.configHolder.set('noCheckImageUrl', True)

        self.configHolder.set('saveDisk', True)

        self.runner = Runner(self.image, self.configHolder)

        self.runner.updateCreateImageTemplateData(
                                    self._getCreateImageTemplateDict())

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
                                                            self.vmStartTimeout,
                                                            failOn=('Failed'))
        if not vmStarted:
            if self.runner.getVmState(self.vmId) == 'Failed':
                msg = 'Failed to start VM (id=%s, ip=%s): %s' % \
                                    (self.vmId, self.vmAddress,
                                     self._getVmFailureMessage(self.vmId))
            else:
                msg = 'Failed to start VM within %i seconds (id=%s, ip=%s)' % \
                                    (self.vmStartTimeout, self.vmId, self.vmAddress)
            self.printDetail(msg)
            self._killMachine()
            self._printError(msg)

    def _stopMachine(self):
        self._printStep('Shutting down machine')

        if self.getVmState() != 'Failed':
                self.cloud.vmStop(self.vmId)

    def _killMachine(self):
        self._printStep('Killing machine')

        if self.vmId:
            self.cloud.vmKill(self.vmId)
        else:
            Util.printWarning('Undefined VM ID, when trying to kill machine.')

    def _getVmFailureMessage(self, vmId):
        return getattr(Monitor(self.configHolder)._vmDetail(vmId),
                       'template_error_message', '')

    def _shutdownNode(self):
        if self.shutdownVm:
            self._stopMachine()
        else:
            self._printStep('Machine ready for your usage')
            print '\n\tMachine IP: %s' % self.vmIp
            print '\tRemember to stop the machine when finished'

    def _waitMachineNetworkUpOrAbort(self):
        self._printStep('Waiting for machine network to start')
        if not waitUntilPingOrTimeout(self.vmAddress, self.vmPingTimeout):
            msg = 'Unable to ping VM in %i seconds (id=%s, ip=%s)' % \
                                    (self.vmPingTimeout, self.vmId, self.vmAddress)
            self._printError(msg)
            self._stopMachine()

    def _getPublicAddress(self):
        return self.vmIp

    def _retrieveManifest(self):
        self._printStep('Retrieving image manifest')
        
        configHolder = self.configHolder.copy()
        
        downloader = ManifestDownloader(configHolder)
        self.manifestObject = downloader.getManifestInfo(self.image)
        self.manifest = self.manifestObject.tostring()

    def __setAttributesFromManifest(self):
        self._setOsFromManifest()
        self._setInstallerBasedOnOs()

    def _setOsFromManifest(self):
        if not self.os:
            self.os = self._getAttrFromManifest('os').lower()

    def _setInstallerBasedOnOs(self):
        if not self.installer:
            self.installer = Systems.getInstallerBasedOnOs(self.os)

    def _getAttrFromManifest(self, attr):
        return getattr(self.manifestObject, attr)

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

    def _setUpExtraRepositories(self):
        if not self.extraOsReposUrls:
            return

        self.printDetail('Adding extra repositories')

        if self.installer not in Systems.INSTALLERS:
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

        self.printDetail('Executing scripts: %s' % self.scripts)

        for script in self.scripts.split(','):
            self._uploadAndExecuteRemoteScript(script)

    def _uploadAndExecuteRemoteScript(self, script):

        def __tellScriptNameAndArgs(script):
            scriptNameAndArgs = os.path.basename(script)
            scriptNameAndArgsList = scriptNameAndArgs.split(' ', 1)
            if len(scriptNameAndArgsList) == 1: # no arguments given
                scriptNameAndArgsList = scriptNameAndArgsList + ['']
            return scriptNameAndArgsList

        def _uploadScript(script):

            scriptName, args = __tellScriptNameAndArgs(script)
            
            scriptDirectory = Util.sanitizePath(os.path.dirname(script))
            scriptPathLocal = '%s/%s' % (scriptDirectory, scriptName)
            scriptPathRemote = '/tmp/%s' % scriptName

            rc, output = self._scpWithOutput(scriptPathLocal, 'root@%s:%s' % (self.vmAddress, scriptPathRemote))
            if rc != 0:
                self._printError('An error occurred while uploading script %s\n%s' % (script, output))
            
            self._sshCmdWithOutput('chmod 0755 %s' % scriptPathRemote)

            return scriptPathRemote, args

        def _executeRemoteScript(scriptPathRemote, args=''):
            rc = self._sshCmd('%s %s' % (scriptPathRemote, args), throwOnError=False,
                              pseudoTTY=True)
            if rc != 0:
                self._printError('An error occurred while executing script %s' % script)

        scriptPathRemote, args = _uploadScript(script)
        _executeRemoteScript(scriptPathRemote, args)

    def _executePrerecipe(self):
        self._printStep('Executing user prerecipe')

        if len(self.prerecipe) == 0:
            self.printDetail('No prerecipe to execute')
            return

        self._uploadAndExecuteRemoteRecipe(self.prerecipe)

    def _executeRecipe(self):
        self._printStep('Executing user recipe')

        if len(self.recipe) == 0:
            self.printDetail('No recipe to execute')
            return

        self._uploadAndExecuteRemoteRecipe(self.recipe)

    def _uploadAndExecuteRemoteRecipe(self, script):

        fd, recipeFile = tempfile.mkstemp()
        try:
            os.write(fd, script)
            os.close(fd)
            os.chmod(recipeFile, 0755)
            scriptPath = '/tmp/%s' % os.path.basename(recipeFile)
            rc = self._scp(recipeFile, 'root@%s:%s' % (self.vmAddress, scriptPath))
            if rc != 0:
                self._printError('An error occurred while uploading recipe')
            self._sshCmdWithOutput('chmod 0755 %s' % scriptPath)
    
            rc = self._sshCmd(scriptPath, throwOnError=False, pseudoTTY=True)
            if rc != 0:
                self._printError('An error occurred while executing user recipe.')
        finally:
            try:
                os.unlink(recipeFile)
            except:
                pass

    def _localCleanUp(self):
        Util.execute(['rm', '-rf', self.manifestLocalFileName])

    def _scp(self, src, dst, **kwargs):
        return Util.scp(src, dst, self.userPrivateKeyFile,
                        verboseLevel=self.verboseLevel, verboseThreshold=Util.DETAILED_VERBOSE_LEVEL,
                        stderr=self.stderr, stdout=self.stdout, **kwargs)
    def _scpWithOutput(self, src, dst):
        return self._scp(src, dst, withOutput=True)

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

    def _sshCmdWithOutputQuiet(self, cmd, **kwargs):
        return self._sshCmdWithOutput(cmd, sshQuiet=True, **kwargs)

    def getNewImageId(self):
        return self.manifestObject.identifier

    def getVmId(self):
        return self.vmId
    
    def getVmState(self):
        return self.runner.getVmState(self.vmId)

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
