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
import os
from datetime import datetime
import time
import urllib2

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Runner import Runner
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
from stratuslab.Util import waitUntilPingOrTimeout
import stratuslab.Util as Util
from Exceptions import ValidationException
from Exceptions import ExecutionException
from ManifestInfo import ManifestInfo
from ConfigParser import SafeConfigParser
from Authn import AuthnFactory

 
class Creator(object):
    
    def __init__(self, image, configHolder):
        self.image = image
        self.configHolder = configHolder
        self.options = Runner.defaultRunOptions()
        self.options.update(configHolder.options)
        configHolder.assign(self)

        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')

        credentials = AuthnFactory.getCredentials(self)
        self.cloud = CloudConnectorFactory.getCloud(credentials)
        self.cloud.setEndpoint(self.endpoint)

        self.runner = None
        self.newManifestFileName = None
        self.vmAddress = None
        self.vmId = None

        # Structure of the repository
        self.appRepoStructure = '#type_#/#os#-#osversion#-#arch#-#type#/#version#'
        # Repository image filename structure
        self.appRepoFilename = '#os#-#osversion#-#arch#-#type#-#version#.img.#compression#'

        self.manifest = None

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
            printError('Failed to reach url %s' % url)
        parser = SafeConfigParser()
        parser.readfp(config)
        self.appRepoStructure = parser.get('stratuslab_repo', 'repo_structure')
        self.appRepoFilename = parser.get('stratuslab_repo', 'repo_filename')

    def _buildConfigFileUrl(self):
        url = self.rootUrl or self._extractRootPath()
        self.printDetail('Using root url: %s' % url)
        return url

    def _extractRootPath(self):
        root = '/'.join(self.image.split('/')[:-4])
        return root

    def _buildRepoNameStructure(self, structure, info):
        varPattern = '#%s#'
        dirVarPattern = '#%s_#'
        for part in ('type', 'os', 'arch', 'version', 'osversion', 'compression', 'author'):
            if structure.find(varPattern % part) != -1:
                structure = structure.replace(varPattern % part, getattr(info, part, ''))

            if structure.find(dirVarPattern % part) != -1:
                structure = structure.replace(dirVarPattern % part, getattr(info, part, '').replace('.', '/'))
        return structure

    def create(self):
        printAction('Starting image creation')

        printStep('Checking that base image exists')
        self._imageExists()
        
        self._createRunner()

        printStep('Starting base image')
        self._startMachine()

        self.vmAddress = self._getPublicAddress()
        
        if not waitUntilPingOrTimeout(self.vmAddress, 600):
            self.cloud.vmStop(self.vmId)
            printError('Unable to ping VM')

        printStep('Creating image manifest')
        self._retrieveManifest()
        self._updateManifest()

        printStep('Installing user packages')
        self._installPackages()

        printStep('Executing user scripts')
        self._executeScripts()

        printStep('Bundling image')
        self._bundleImage()

        printStep('Uploading image to appliance repository')
        self._upload()

        if self.shutdownVm:
            printStep('Shutting down machine')
            self.cloud.vmStop(self.vmId)
        else:
            printStep('Machine ready for your usage')
            print '\n\tMachine IP: %s' % ', '.join(dict(self.vmIps).values())
            print '\tRemember to stop the machine when finished',
            
        printAction('Image creation finished')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (self.stdout.name,
                                                                        self.stderr.name)
    def _imageExists(self):
        self._pingImage()
        self._pingManifest()
    
    def _pingImage(self):
        ending = 'img.gz'
        if not self.image.endswith(ending):
            raise ValidationException('Image file must end with: %s' % ending)
        if not Util.pingFile(self.image, 'application/x-gzip'):
            raise ValidationException('Unable to access the base image: %s' % self.image)

    def _pingManifest(self):
        url = self.image[:-7] + '.xml'
        if not Util.pingFile(url, 'text/xml'):
            raise ValidationException('Unable to access manifels file: %s' % url)

    def _createRunner(self):
        self.configHolder.set('extraDiskSize', 8*1024)
        self.runner = Runner(self.image, self.configHolder)
        
    def _startMachine(self):
        try:
            self.vmIds = self.runner.runInstance()
            self.vmIps = self.runner.vmIps
        except Exception, msg:
            printError('An error occurred while starting machine: \n\t%s' % msg)

        self.vmId = self.vmIds[0]
        printStep('Waiting for machine to boot')
        vmStarted = self.runner.waitUntilVmRunningOrTimeout(self.vmId)
        if not vmStarted:
            printError('Failed to start VM!')

    def _getPublicAddress(self):
        return dict(self.vmIps)['public']

    def _retrieveManifest(self):
        self.printDetail('Retrieving Manifest')
        manifestFileName = self.image[:-6] + 'xml'
        self.manifest = Util.wstring(manifestFileName)

    def _updateManifest(self):
        self.printDetail('Updating manifest')
        info = ManifestInfo()
        info.parseManifest(self.manifest)

        info.created = time.time()
        info.type = self.newImageGroupName or info.type
        info.os = self.newInstalledSoftwareName or info.os
        info.osversion = self.newInstalledSoftwareVersion or info.osversion
        info.user = self.author or info.user
        info.version = self.newImageGroupVersion or info.version
        info.comment = self.comment or info.comment
        
        self.manifest = info.tostring()
        
        return info

    def _installPackages(self):
        if len(self.packages) == 0:
            printStep('No packages to install')
            return
        
        printStep('Installing packages: ' % self.packages)
        
        cmd = self._buildInstallerCommand() + ' '
        cmd += ' '.join(self.packages.split(','))
        ret = sshCmd(cmd, self.vmAddress, self.sshKey,
               stderr=self.stderr, stdout=self.stdout)

        if ret != 0:
            printError('An error occurred while installing packages')

    def _buildInstallerCommand(self):
        # TODO: do this properly
        return 'yum -q -y --nogpgcheck install'

    def _executeScripts(self):
        if len(self.scripts) == 0:
            printStep('No scripts to execute')
            return

        printStep('Executing scripts: ' % self.scripts)

        for script in self.scripts.split(','):
            scriptPath = '/tmp/%s' % os.path.basename(script)
            scp(script, 'root@%s:%s' % (self.vmAddress, scriptPath),
                self.sshKey, stderr=self.stderr, stdout=self.stdout)

            ret = sshCmd('%s' % scriptPath, self.vmAddress, self.sshKey,
                         stderr=self.stderr, stdout=self.stdout)

            if ret != 0:
                printError('An error occurred while executing script %s' % script)


    def _bundleImage(self):
        self._removeFilesForExclusion()
                
        printStep('Mounting the extra disk for bundling')
        mountPoint = '/extra-disk'
        self._sshCmd('mkdir -p %s' % mountPoint)
        self._sshCmd('mount /dev/hdd %s' % mountPoint)
        
        printStep('Bundling')
        newImageName = '/tmp/newimage.img.gz'
        ddCmd = 'dd if=/dev/hda conv=sync,noerror bs=64K | gzip -c  > %s' % newImageName
        sshCmd(ddCmd)
        
    def _removeFilesForExclusion(self):
        printStep('Removing files/directories to be excluded')
        excludeFiles = self.excludeFromBundle + ', /tmp, /mnt'
        self._sshCmd('rm -rf %s' % ' '.join(excludeFiles.split(',')))

    def _sshCmd(self, cmd, throwOnError=True):
        ret = sshCmd(cmd)
        if ret and throwOnError:
            raise ExecutionException('Error executing command: %s' % cmd)
        return ret
        
    def _upload(self):
        name = self._constructImageName()
        pass
