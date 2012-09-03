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
        
    def __init__(self):
        self.installAllComponents = False  
    
    @staticmethod
    def availableInstallator():
        return {'opennebula': OpenNebula,
                'persistent-disk': PersistentDisk,
                'web-monitor': WebMonitor,
                'registration': Registration,
                'port-translation': PortTranslation,
                'openldap': OpenLDAP,
                'sunstone' : Sunstone }
        
    def runInstallator(self, configHolder):
        self.configHolder = configHolder
        configHolder.assign(self)
        
        self._selectAllComponentsIfNoneSpecified()
        self._launchInstallator()
        
    def _selectAllComponentsIfNoneSpecified(self):
        selectedCompoments = []
        for name in self.availableInstallator().keys():
            selectedCompoments.append(getattr(self, 'install%s' % name.title()))
        self.installAllComponents = not any(selectedCompoments)
        printDetail('All components selected: %s' % self.installAllComponents, self.verboseLevel, 3)
 
    def _launchInstallator(self):
        for componentName, installer in self.availableInstallator().items():
            if self._isComponentSelected(componentName):
                componentInstallator = installer(self.configHolder)
                self._executeInstall(componentName, componentInstallator)
                
    def _isComponentSelected(self, name):
        return (getattr(self, 'install%s' % name.title()) 
                or self._selectedInConfig(name)
                or self.installAllComponents)

    def _executeInstall(self, componentName, componentInstallator):
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
            
    def _selectedInConfig(self, value):
        return isTrueConfVal(value.replace('-', '_'))
