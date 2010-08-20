import subprocess
from datetime import datetime

from stratuslab.Runner import Runner
from stratuslab.Util import assignAttributes
from stratuslab.Util import getSystemMethods
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import randomString
from stratuslab.Util import scp
from stratuslab.Util import sshCmd
from stratuslab.Util import waitUntilPingOrTimeout

class Creator(object):
    def __init__(self, image, options, config):
        self.config = config
        self.image = image
        self.options = Runner.defaultRunOptions()
        self.options.update(options)
        assignAttributes(self, self.options)

        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
        self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')

        self.runner = None
        self.vmIps = None
        self.vmId = None

    def __del__(self):
        self.stderr.close()
        self.stdout.close()

    def _buildRunner(self):
        self.sshKey = '/tmp/%s' % randomString()
        self.options['saveDisk'] = True

        self.runner = Runner(self.image, self.options, self.config)
        self.runner.creator_context = '%s\n'.join(self._buildRunnerContext())
        self.runner.creator_key = self.sshKey

    def _buildRunnerContext(self):
        context = {}
        context['stratuslab_ssh_key'] = self.sshKey

        createImgOpt = [
            self.uploadProtocol,
            self.repoAddress,
            self.archiveFormat,
            self.repoUsername,
            self.repoPassword,
            str(self.forceUpload),
        ]
        context['stratuslab_create_image'] = ' '.join(createImgOpt)

        return ['%s = "%s",' % (key, value) for key, value in context.items()]

    def _startMachine(self):
        try:
            self.runner.runInstance()
        except Exception, msg:
            printError('An error occured while starting machine: \n\t%s' % msg)
            
        if not self.cloud.waitUntilVmRunningOrTimeout(self.vmId, 60):
            printError('Unable to boot VM')

    def _getVmSystem(self):
        system = 'unknow'
        version = '0'

        try:
            system, version = self._findRedHatSystem()
        except:
            try:
                system, version = self._findDebianSystem()
            except:
                return

        return system, version

    def _findRedHatSystem(self):
        devNull = open('/dev/null', 'w')
        redHatDistro = sshCmd('cat /etc/redhat-release', self.vmAddress, self.sshKey, noWait=True,
                              stdout=subprocess.PIPE, stderr=devNull).communicate()[0]
        devNull.close()

        if redHatDistro:
            raise

        system = redHatDistro.split(' ')[0].lower()
        version = redHatDistro.split(' ')[2]
        return system, version

    def _findDebianSystem(self):
        devNull = open('/dev/null', 'w')
        debianDistro = sshCmd('cat /etc/lsb-release', self.vmAddress, self.sshKey, noWait=True,
                              stdout=subprocess.PIPE, stderr=devNull).communicate()[0]
        devNull.close()

        if debianDistro:
            raise

        for line in debianDistro.split('\n'):
            if line.startswith('DISTRIB_ID'):
                system = line.split('=')[1].lower()
            elif line.startswith('DISTRIB_RELEASE'):
                version = line.split('=')[1]
                
        return system, version

    def _installPackages(self):
        os, _ = self._getVmSystem()
        system = getSystemMethods(os)

        if len(self.packages) == 0:
            return
        
        ret = sshCmd('%s %s' % (system.installCmd, self.packages),
                      self.vmAddress, self.sshKey, stderr=self.stderr, stdout=self.stdout)

        if ret != 0:
            printError('An error occured while installing packages')

    def _executeScripts(self):
        if len(self.scripts) == 0:
            return

        for script in self.scripts.split(' '):
            scp(script, 'root@%s:' % self.vmAddress, self.sshKey, 
                stderr=self.stderr, stdout=self.stdout)

            ret = sshCmd('bash %s' % script, self.vmAddress, self.sshKey,
                         stderr=self.stderr, stdout=self.stdout)
            sshCmd('rm -fr %s' % script, self.vmAddress, self.sshKey)

            if ret != 0:
                printError('An error occured while executing script %s' % script)

    def create(self):
        printAction('Starting image creation')
        
        printStep('Creating machine template')
        self._buildRunner()

        self._startMachine()

        printStep('Waiting for network interface to be up')
        self.vmAddress = self.vmIps(self.vmId).get(self.interface)
        
        if not waitUntilPingOrTimeout(self.vmAddress, 20):
            self.cloud.vmStop(self.vmId)
            printError('Unable to ping VM')

        printStep('Installing user packages')
        self._installPackages()

        printStep('Executing user scripts')
        self._executeScripts()

        if self.shutdownVm:
            printStep('Shutting down machine')
            self.cloud.vmStop(self.vmId)
        else:
            printStep('Machine ready for your usage')
            print '\n\tMachine IP:'
            print '\tRemember to stop the machine when finished',
            
        printAction('Image creation finished')
        print '\n\tInstallation details can be found at: \n\t%s, %s' % (self.stdout.name,
                                                                        self.stderr.name)
