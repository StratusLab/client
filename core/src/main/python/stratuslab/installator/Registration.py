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
from stratuslab import Util, Defaults
from stratuslab.Util import printStep, filePutContent, fileGetContent, \
    restartService
from stratuslab.installator.Installator import Installator
import os
import stratuslab.system.SystemFactory as SystemFactory


class Registration(Installator):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['apacheds']
    
    # TODO: Remove if not used    
    def run(self):
        self._installPackages()
        self.setup()
        self._restartService('one-proxy')
        
    def _installFrontend(self):
        printStep('Installing packages')
        self.system.installPackages(self.packages)

    def _setupFrontend(self):
        printStep('Creating registration configuration file')
        registrationTpl = os.path.join(Util.getTemplateDir(), 'registration.cfg.tpl')
        registrationConfFile = os.path.join(Defaults.ETC_DIR, 'registration.cfg') 
        self._writeConfigFromTemplate(registrationConfFile, registrationTpl)
        
    def _writeConfigFromTemplate(self, config, tpl):
        filePutContent(config,
                       fileGetContent(tpl) % self.__dict__)
       
    def _startServicesFrontend(self):
        restartService('one-proxy')

