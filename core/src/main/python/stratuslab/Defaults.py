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
import os.path as path

userHome = path.expanduser('~')

sshPublicKeyLocation = path.join(userHome, '.ssh/id_rsa.pub')

_globusDirectory = path.join(userHome, '.globus')

pemDirectory = _globusDirectory
pemCertificateFile = 'usercert.pem'
pemKeyFile = 'userkey.pem'
pemCertificateLocation = path.join(pemDirectory, pemCertificateFile)
pemKeyLocation = path.join(pemDirectory, pemKeyFile)

p12Directory = _globusDirectory
p12CertificateFile = 'usercert.p12'
p12CertificateLocation = path.join(p12Directory, p12CertificateFile)

marketplaceEndpoint = 'http://appliances.stratuslab.eu/marketplace/metadata'

apprepoEndpoint = 'http://appliances.stratuslab.eu/images'