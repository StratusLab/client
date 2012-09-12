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

from stratuslab.Util import printAction, isTrueConfVal, printDetail
from stratuslab.installator.PersistentDisk import PersistentDisk
from stratuslab.installator.WebMonitor import WebMonitor
from stratuslab.installator.OpenNebula import OpenNebula
from stratuslab.installator.Registration import Registration
from stratuslab.installator.Sunstone import Sunstone
from stratuslab.installator.PortTranslation import PortTranslation
from stratuslab.installator.OpenLDAP import OpenLDAP

class BaseInstallator(object):
    
    @staticmethod
    def availableInstallators():
        return (('opennebula', OpenNebula),
                ('persistent-disk', PersistentDisk),
                ('web-monitor', WebMonitor),
                ('openldap', OpenLDAP),
                ('registration', Registration),
                ('port-translation', PortTranslation),
                ('sunstone', Sunstone))

    @staticmethod
    def availableInstallatorNames():
        return tuple(map(lambda x: x[0], 
                         BaseInstallator.availableInstallators()))

    @staticmethod
    def installatorNameToConfParamName(name):
        return name.replace('-', '_')

    def runInstallator(self, configHolder):
        self._assignConfigHolder(configHolder)

        components = self._selectCompenentsToInstall()
        self._launchInstallator(components)

    def _assignConfigHolder(self, configHolder):
        self.configHolder = configHolder
        configHolder.assign(self)

    def _selectCompenentsToInstall(self):
        componentsToInstall = []

        componentsToInstall.extend(self._getComponentsSelectedInOptions())

        if not componentsToInstall:
            componentsToInstall.extend(self._getComponentsSelectedInConfig())

        componentsToInstall = tuple(componentsToInstall)

        printDetail('Components selected: %s' % ', '.join(componentsToInstall), 
                    self.verboseLevel, 3)

        return componentsToInstall

    def _getComponentsSelectedInOptions(self):
        components = []
        for name in self.availableInstallatorNames():
            if self._isComponentSelectedInOptions(name):
                components.append(name)
        return components

    def _getComponentsSelectedInConfig(self):
        components = []
        for name in self.availableInstallatorNames():
            if self._isComponentSelectedInConfig(name):
                components.append(name)
        return components

    def _isComponentSelectedInOptions(self, name):
        return getattr(self, 'install%s' % name.title())

    def _isComponentSelectedInConfig(self, name):
        selected = self.configHolder.config.get(self.installatorNameToConfParamName(name), 
                                                False)
        return isTrueConfVal(selected)

    def _launchInstallator(self, componentsToInstall):
        for componentName, installerClass in self.availableInstallators():
            if componentName in componentsToInstall:
                self._executeInstall(componentName, installerClass)

    def _executeInstall(self, componentName, installerClass):
        componentInstallator = installerClass(self.configHolder)

        self._installStep(componentName, componentInstallator)
        self._setupStep(componentName, componentInstallator)
        self._startService(componentName, componentInstallator)

    def _installStep(self, componentName, componentInstallator):
        if self.installStep:
            printAction('Installing %s' % componentName)
            componentInstallator.install()

    def _setupStep(self, componentName, componentInstallator):
        if self.setupStep:
            printAction('Setting up %s' % componentName)
            componentInstallator.setup()

    def _startService(self, componentName, componentInstallator):
        if self.startComponent:
            printAction('Starting %s services' % componentName)
            componentInstallator.startServices()
