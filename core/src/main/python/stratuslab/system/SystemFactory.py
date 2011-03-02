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
import stratuslab.Util as Util

def getSystem(system, configHolder):
    moduleDir = os.path.dirname(__file__)

    if not os.path.isfile('%s/%s.py' % (moduleDir, system)):
        raise ValueError('Failed to find system module %s' % system)

    Util.setPythonPath(moduleDir)

    module = Util.importSystem(system)

    obj = getattr(module, 'system')
    configHolder.assign(obj)
    obj.init()
    
    return obj
