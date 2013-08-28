import os
import re
import socket
import stratuslab.Util as Util
from stratuslab import Defaults
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Util import printStep, fileGetContent
from stratuslab.system import SystemFactory
from stratuslab.installator.Installator import Installator
from stratuslab.Exceptions import ExecutionException

class VMUsage(Installator):

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        self.configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.nodeSystem, self.configHolder)
	self.packages = ['stratuslab-vmusage']        

    def _installNode(self):
        self.system.workOnNode()
        self.system.installNodePackages(self.packages)

    def _setupNode(self):
        printStep('Creating monitoring configuration file')
        monitoringTpl = os.path.join(Util.getTemplateDir(), 'monitoring.cfg.tpl')
        monitoringConfFile = os.path.join(Defaults.ETC_DIR, 'monitoring.cfg')
        self._writeConfigFromTemplate(monitoringConfFile, monitoringTpl)

    def _writeConfigFromTemplate(self, config, tpl):
        filePutContent(config,
                       fileGetContent(tpl) % self.__dict__)        

        
