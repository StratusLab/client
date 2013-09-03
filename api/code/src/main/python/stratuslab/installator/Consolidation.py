import os

from stratuslab import Util, Defaults
from stratuslab.Util import printStep, filePutContent, fileGetContent
from stratuslab.installator.Installator import Installator
import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.Exceptions import ValidationException

class Consolidation(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['stratuslab-consolidation']
        
    def _installFrontend(self):
        printStep('Installing packages')
        self.system.installPackages(self.packages)

    def _setupFrontend(self):
        printStep('Creating monitoring configuration file')
        monitoringTpl = os.path.join(Util.getTemplateDir(), 'monitoring.cfg.tpl')
        monitoringConfFile = os.path.join(Defaults.ETC_DIR, 'monitoring.cfg') 
        self._writeConfigFromTemplate(monitoringConfFile, monitoringTpl)

    def _writeConfigFromTemplate(self, config, tpl):
        filePutContent(config,
                       fileGetContent(tpl) % self.__dict__)
       
