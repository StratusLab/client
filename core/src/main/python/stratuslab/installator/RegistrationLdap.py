#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique
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

class RegistrationLdap(object):

    def __init__(self, configHolder):
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        self.packages = ['openldap-servers', 'openldap-clients']
        
    def run(self):
        self._installPackages()
        self._configure()
        self._restartService('slapd')
        
    def _installPackages(self):
        Util.printStep('Installing packages')
        self.system.installPackages(self.packages)

    def _configure(self):
        Util.printStep('Creating LDAP configuration files')
        
        baseInfoTpl = os.path.join(Util.getTemplateDir(), 'base.ldif.tpl')
        baseInfoFile = os.path.join(Defaults.ETC_DIR, 'base.ldif') 
        Util.filePutContent(baseInfoFile,
                            Util.fileGetContent(baseInfoTpl) % self.__dict__)

    def _restartService(self, service):
        Util.printStep("Adding slapd to chkconfig and restarting")
        cmd = 'chkconfig --add %s' % service
        Util.execute(cmd.split(' '))
        cmd = 'service %s restart' % service
        Util.execute(cmd.split(' '))
