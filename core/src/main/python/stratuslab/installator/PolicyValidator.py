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
from stratuslab import Defaults
from stratuslab.marketplace.Policy import Policy
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.OneDefaults import OneDefaults

class PolicyValidator(object):
    
    TEMPLATE_CFG = os.path.join(Util.getTemplateDir(), 'policy.cfg.tpl')
    CONFIG = os.path.join(Defaults.ETC_DIR, Policy.POLICY_CFG) 
    CONFIG_SAV = CONFIG + '.sav'
    ONE_SCRIPTS_CONFIGS = [os.path.join(OneDefaults.CLOUD_CONF_DIR,'tm_ssh/tm_ssh.conf')]

    def __init__(self, configHolder=ConfigHolder()):
        configHolder.assign(self)
        
    def run(self):
        self._configure()
        
    def _configure(self):

        if self._backupConfigFileExists():
            Util.printWarning("Policy validation backup file %s already exists, skipping configuration" % PolicyValidator.CONFIG_SAV)
            return

        Util.printStep('Creating policy validation configuration file')

        self._backup()

        Util.filePutContent(PolicyValidator.CONFIG,
                            Util.fileGetContent(PolicyValidator.TEMPLATE_CFG) % self.__dict__)

    def resetOneConfig(self):
        Util.printStep('Reseting ONE extension policy configuration')
        # Hack... try twice so that we don't mask the script for caching
        sedCmdsPart = ['s/tm_clone_policy.sh/tm_clone.sh/g ',
                       's/tm_clone_policy_caching.sh/tm_clone_caching.sh/g ']
        self._updateOneConfig(sedCmdsPart)

    def _updateOneConfig(self, sedCmdsPart):
        for config in PolicyValidator.ONE_SCRIPTS_CONFIGS:
            cmd = 'sed -i ' + ' '.join(["-e '" + part + "'" for part in sedCmdsPart]) + ' ' + config
            self._execute(cmd)

    def _backupConfigFileExists(self):
        return os.path.exists(PolicyValidator.CONFIG_SAV)
    
    def _backup(self):
        if os.path.exists(PolicyValidator.CONFIG):
            shutil.move(PolicyValidator.CONFIG, PolicyValidator.CONFIG_SAV)
    
    def _execute(self, cmd):
        return Util.execute(cmd, shell=True)
