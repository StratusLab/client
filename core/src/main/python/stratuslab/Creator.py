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
import base64
import os
import pickle
from datetime import datetime

from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Runner import Runner
from stratuslab.Util import assignAttributes
from stratuslab.Util import cliLineSplitChar
from stratuslab.Util import fileGetContent
from stratuslab.Util import generateSshKeyPair
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import randomString
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
from stratuslab.Util import waitUntilPingOrTimeout
import stratuslab.Util as Util

 
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

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setEndpoint(self.endpoint)

        self.cloud.setCredentials(self.username, self.password)

        self.sshKey = '/tmp/%s' % randomString()
        generateSshKeyPair(self.sshKey)

        self.vmManifestPath = '/tmp/disk.0.manifest.xml' # Location of the manifest on the VM
        self.packageInstallScript = Util.shareDir + 'creation/install-pkg.sh'
        self.manifestCreationScript = Util.shareDir + 'creation/create-manifest.sh'

        self.runner = None
        self.vmIps = {}
        self.vmIds = []
        self.vmId = None

    def __del__(self):
        self.stderr.close()
        self.stdout.close()

    def _buildRunner(self):
        self.options['saveDisk'] = True

        self.runner = Runner(self.image, self.configHolder)
        self._addCreationContext()
        
    def _addCreationContext(self):
        context = [
            'stratuslab_remote_key=%s' % fileGetContent(self.sshKey + '.pub'),
            'stratuslab_manifest=%s' % self.vmManifestPath,
            'stratuslab_upload_info=%s' %  self._buildUploadInfoContext()
        ]

        context.extend(self.runner.extraContextData.split(cliLineSplitChar))
        self.runner.extraContextData = cliLineSplitChar.join(context)

    def _buildUploadInfoContext(self):
        uploadInfoElem = [ 'repoAddress', 'compressionFormat', 'forceUpload',
                           'uploadOption', 'repoUsername', 'repoPassword' ]

        uploadInfoDict = {}
        for elem in uploadInfoElem:
            uploadInfoDict[elem] = getattr(self, elem, '')

        return base64.urlsafe_b64encode(pickle.dumps(uploadInfoDict))

    def _startMachine(self):
        try:
            self.vmIds = self.runner.runInstance()
            self.vmIps = self.runner.vmIps
        except Exception, msg:
            printError('An error occured while starting machine: \n\t%s' % msg)

        self.vmId = self.vmIds[0]
        vmStarted = self.runner.waitUntilVmRunningOrTimeout(self.vmId)
        if not vmStarted:
            printError('Failed to start VM!')

    # TODO: Create a generic method to run script on the VM

    def _createImageManifest(self):
        separatorChar = '%'
        imageDefinition = [self.imageName, self.imageVersion, self.username, self.vmManifestPath]
        scriptOnVm = '/tmp/create-manifest.sh'

        scp(self.manifestCreationScript, 'root@%s:%s' % (self.vmAddress, scriptOnVm),
            self.sshKey, stderr=self.stderr, stdout=self.stdout)

        ret = sshCmd('bash %s %s %s' % (scriptOnVm, separatorChar, separatorChar.join(imageDefinition)),
                     self.vmAddress, self.sshKey, stderr=self.stderr, stdout=self.stdout)

        sshCmd('rm -rf %s' % scriptOnVm, self.vmAddress, self.sshKey,
               stderr=self.stderr, stdout=self.stdout)

        if ret != 0:
            printError('An error occurred while creating image manifest')

    def _installPackages(self):
        if len(self.packages) == 0:
            return

        scriptOnVm = '/tmp/install-pkg.sh'

        scp(self.packageInstallScript, 'root@%s:%s' % (self.vmAddress, scriptOnVm),
            self.sshKey, stderr=self.stderr, stdout=self.stdout)
        
        ret = sshCmd('bash %s %s' % (scriptOnVm, self.packages), self.vmAddress,
                     self.sshKey, stderr=self.stderr, stdout=self.stdout)

        sshCmd('rm -rf %s' % scriptOnVm, self.vmAddress, self.sshKey,
               stderr=self.stderr, stdout=self.stdout)

        if ret != 0:
            printError('An error occured while installing packages')

    def _executeScripts(self):
        if len(self.scripts) == 0:
            return

        for script in self.scripts.split(' '):
            scriptPath = '/tmp/%s' % os.path.basename(script)
            scp(script, 'root@%s:%s' % (self.vmAddress, scriptPath),
                self.sshKey, stderr=self.stderr, stdout=self.stdout)

            ret = sshCmd('bash %s' % scriptPath, self.vmAddress, self.sshKey,
                         stderr=self.stderr, stdout=self.stdout)

            sshCmd('rm -fr %s' % scriptPath, self.vmAddress, self.sshKey)

            if ret != 0:
                printError('An error occured while executing script %s' % script)

    def create(self):
        printAction('Starting image creation')
        
        printStep('Creating machine template')
        self._buildRunner()

        self._startMachine()

        printStep('Waiting for network interface to be up')
        self.vmAddress = dict(self.vmIps).get(self.interface)
        
        if not waitUntilPingOrTimeout(self.vmAddress, 600):
            self.cloud.vmStop(self.vmId)
            printError('Unable to ping VM')

        printStep('Creating image manifest')
        self._createImageManifest()

        printStep('Installing user packages')
        self._installPackages()

        printStep('Executing user scripts')
        self._executeScripts()

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
