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
from stratuslab.system.centos import CentOS
from stratuslab.system.PackageInfo import PackageInfo

class Fedora(CentOS):
    
    os = 'fedora'
    
    def __init__(self):
        super(Fedora, self).__init__()
        self.frontendDeps = [
                'openssh', 'ruby', 'zlib-devel', 'curl'
        ]
        
        self.packages['dhcp'] = PackageInfo('dhcp',
                                            configFile='/etc/dhcp/dhcpd.conf',
                                            initdScriptName='dhcpd')
        

system = Fedora()
