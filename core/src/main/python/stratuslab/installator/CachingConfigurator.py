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
import shutil

from stratuslab import Util
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.OneDefaults import OneDefaults

class CachingConfigurator(object):
    
    ONE_SCRIPTS_CONFIGS = [os.path.join(OneDefaults.CLOUD_CONF_DIR, 'tm_ssh/tm_ssh.conf')]

    def __init__(self, configHolder=ConfigHolder()):
        configHolder.assign(self)
        
    def resetOneConfig(self):
        Util.printStep('Reseting ONE extension caching configuration')
        # Hack... try twice so that we don't mask the script for caching
        sedCmdsPart = ['s/tm_clone_caching.sh/tm_clone.sh/g',
                       's/tm_clone_policy_caching.sh/tm_clone_policy.sh/g']
        self._updateOneConfig(sedCmdsPart)

    def run(self):
        self._configure()
        
    def _configure(self):
        self._addPolicyToOneConfig()

    def _addPolicyToOneConfig(self):
        Util.printStep('Updating ONE extension caching configuration')
        # Hack... try twice so that we don't mask the script for caching
        sedCmdsPart = ['s/tm_clone.sh/tm_clone_caching.sh/g',
                       's/tm_clone_policy.sh/tm_clone_policy_caching.sh/g']
        self._updateOneConfig(sedCmdsPart)

    def _updateOneConfig(self, sedCmdsPart):
        for config in CachingConfigurator.ONE_SCRIPTS_CONFIGS:
            cmd = 'sed -i ' + ' '.join(["-e '" + part + "' " for part in sedCmdsPart]) + ' ' + config
            self._execute(cmd)

    def _execute(self, cmd):
        return Util.execute(cmd, shell=True)
