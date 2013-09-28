#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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

from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.vm_manager.Runner import Runner


class VmManagerFactory:
    def __init__(self):
        pass

    @staticmethod
    def create(image, config_holder=None):
        """
        Creates a VM manager instance based on the requested
        type in the given ConfigHolder object.  If the field
        vm_manager_type is in the ConfigHolder then that type
        will be instantiated and returned.
        """
        if config_holder is None:
            config_holder = ConfigHolder()

        if hasattr(config_holder, 'vm_manager_type'):
            vm_manager_type = config_holder.vm_manager_type
        else:
            vm_manager_type = 'one'

        if vm_manager_type == 'one':
            return Runner(image, config_holder)
        else:
            raise NotImplementedError('unknown VM manager type: %s' % vm_manager_type)
