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
from os.path import join, expanduser

userHome = expanduser('~')

sshPublicKeyLocation = join(userHome, '.ssh', 'id_rsa.pub')

_globusDirectory = join(userHome, '.globus')

pemDirectory = _globusDirectory
pemCertificateFile = 'usercert.pem'
pemKeyFile = 'userkey.pem'
pemCertificateLocation = join(pemDirectory, pemCertificateFile)
pemKeyLocation = join(pemDirectory, pemKeyFile)

p12Directory = _globusDirectory
p12CertificateFile = 'usercert.p12'
p12CertificateLocation = join(p12Directory, p12CertificateFile)

marketplaceEndpoint = 'https://marketplace.stratuslab.eu'
marketplaceProtocol = 'https'
marketplaceHostname = 'marketplace.stratuslab.eu'
marketplacePort = 80

pdiskPort = 8445
pdiskProtocol = 'https'

portTranslation = False
patServiceDbname = '/var/lib/one/ports.db'
patPortsRange = '15000:17000'
patTranslatedPorts = [22]
patNetworks = ['local']
patFirewallChainPrefix = 'PAT'
patMaxTranslations = 0
patVerboseLevel = 0

ETC_DIR = '/etc/stratuslab'
SHARE_DIR = '/var/share/stratuslab'
ONE_PROXY_DIR = '/opt/stratuslab/one-proxy'

AUTHN_CONFIG_FILE = ETC_DIR + '/authn/login-pswd.properties'

SHARE_TYPE = 'stratuslab'

CLOUD_CONF_DIR = '/etc/one/'
CLOUD_CONF_FILE = CLOUD_CONF_DIR + 'oned.conf'

CLOUD_VAR_LIB_DIR = '/var/lib/one'

