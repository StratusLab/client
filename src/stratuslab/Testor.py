from stratuslab.CloudConnectorFactory import CloudConnectorFactory
from stratuslab.Util import fileGetContent
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import modulePath
from stratuslab.Runner import Runner

class Testor(object):
    
    def __init__(self, config, options):
        self.config = config
        self.options = options

        self.cloud = CloudConnectorFactory.getCloud()
        self.cloud.setFrontend(self.config.get('frontend_ip'),
                               self.config.get('one_port'))
        self.cloud.setCredentials(self.config.get('one_username'),
                                  self.config.get('one_password'))
        
        # Attributes initialization
        self.vmTemplate = None
        self.vmId = None
        
        
    def runTests(self):
        printAction('Launching smoke test')
        
        printStep('Starting VM')
        self.startVmTest()
        
        printStep('Ping VM')
        self.ping()
        
        printStep('Logging to VM via SSH')
        self.loginViaSsh()
        
        printStep('Shutting down VM')
        self.stopVmTest()

        printAction('Smoke test finished')
    
    def startVmTest(self):
        self.buildVmTemplate()

        options = Runner.defaultRunOptions()
        options['username'] = self.config['one_username']
        options['password'] = self.config['one_password']

        image = 'https://appliances.stratuslab.org/images/base/ubuntu-10.04-i686-base/1.0/ubuntu-10.04-i686-base-1.0.img.tar.gz'
        runner = Runner(image, options, self.config)
        runner.runInstance()
        
        self.vmId = self.cloud.vmStart(self.vmTemplate)
        
        vmStarted = self.cloud.waitUntilVmRunningOrTimeout(self.vmId, 120)
        
        if not vmStarted:
            printError('Failing to start VM')
        
    def buildVmTemplate(self):
        self.vmTemplate = fileGetContent(self.options.vmTemplate) % self.config
    
    def ping(self):

        for endpoint in self.getIpAddresses():
            print 'Pinging', endpoint
            res = Util.ping(endpoint)
            if res:
                raise Exception('Failed to ping %s with return code %s' % (endpoint, res))
        
    def loginViaSsh(self):

        loginCommand = 'ls /tmp'

        for networkName, ip in self.getIpAddresses().items():
            print 'SSHing into machine at via address %s at ip %s' % (networkName, ip)
            res = Util.sshCmd(loginCommand, ip, self.config.get('node_private_key'))
            if res:
                raise Exception('Failed to SSH into machine for %s with return code %s' % (endpoint, res))
        
    def getIpAddresses(self):
        return self.cloud.getVmIp(self.vmId)
    
    def stopVmTest(self):
        vmStopped = self.cloud.vmStop(self.vmId)
        
        if not vmStopped:
            printError('Failing to stop VM')
