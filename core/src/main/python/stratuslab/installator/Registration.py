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

import stratuslab.system.SystemFactory as SystemFactory
from stratuslab import Util, Defaults

class Registration(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['apacheds']
        
    def run(self):
        self._installPackages()
        self._configure()
        self._restartService('authn-proxy')
        
    def _installPackages(self):
        Util.printStep('Installing packages')
        self.system.installPackages(self.packages)

    def _configure(self):
        Util.printStep('Creating registration configuration file')
        
        registrationTpl = os.path.join(Defaults.TEMPLATE_DIR, 'registration.cfg.tpl')
        registrationConfFile = os.path.join(Defaults.ETC_DIR, 'registration.cfg') 
        Util.filePutContent(registrationConfFile,
                            Util.fileGetContent(registrationTpl) % self.__dict__)

    def _restartService(self, service):
        Util.printStep("Restarting Jetty7 (authn-proxy)")
        cmd = 'service %s restart' % service
        Util.execute(cmd.split(' '))
