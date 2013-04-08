#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010, SixSq Sarl
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
import commands
import tempfile
import shutil

from stratuslab.Exceptions import ExecutionException
import stratuslab.Util as Util
from stratuslab.ConfigHolder import ConfigHolder


class CertGenerator(object):
    descriptionP12 = 'generate p12 self-signed certificate.'

    def __init__(self, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        self.tmp_dir = ''

    @staticmethod
    def defaultRunOptionsP12():
        return {'commonName': 'Jane Tester',
                'outputFile': 'cert.p12',
                'certPassword': 'XYZXYZ',
                'certValidity': '365',
                'subjectEmail': 'jane.tester@example.org'}

    @staticmethod
    def addCertGeneratorOptions(parser):
        defaults = CertGenerator.defaultRunOptionsP12()

        parser.add_option('-n', '--common-name', dest='commonName',
                          help='Common Name for the certificate. (Default: %s)' %
                               defaults['commonName'],
                          default=defaults['commonName'], metavar='NAME')

        parser.add_option('-o', '--output', dest='outputFile',
                          help='file to store the generated certificate (Default: %s)' %
                               defaults['outputFile'],
                          default=defaults['outputFile'], metavar='FILE')

        parser.add_option('-p', '--password', dest='certPassword',
                          help='password for the certificate. (Default: %s)' %
                               defaults['certPassword'],
                          default=defaults['certPassword'], metavar='PASS')

        parser.add_option('--validity', dest='certValidity',
                          help='validity of the certificate. (Default: %s)' %
                               defaults['certValidity'],
                          default=defaults['certValidity'], metavar='DAYS')

        parser.add_option('-e', '--email', dest='subjectEmail',
                          help='subject email. (Default: %s)' %
                               defaults['subjectEmail'],
                          default=defaults['subjectEmail'], metavar='EMAIL')

        parser.add_option('--no-cleanup', dest='noCleanup',
                          help='do not do cleanup.',
                          default=False, action='store_true')

    @staticmethod
    def buildCertGeneratorP12Parser(parser):
        parser.description = CertGenerator.descriptionP12
        CertGenerator.addCertGeneratorOptions(parser)

    def generateP12(self):
        self.tmp_dir = tempfile.mkdtemp()
        Util.printDetail('Temporary directory for certificate generation: %s' %
                         self.tmp_dir, self.configHolder.verboseLevel,
                         Util.VERBOSE_LEVEL_DETAILED)
        try:
            self._generateOpensslConfig()
            self._runCommandsP12()
        finally:
            if self.configHolder.noCleanup:
                Util.printInfo('Intermediate files are in %s' % self.tmp_dir)
            else:
                try:
                    shutil.rmtree(self.tmp_dir, ignore_errors=True)
                except:
                    pass

    def _generateOpensslConfig(self):
        config = """
[ req ]
distinguished_name     = req_distinguished_name
x509_extensions        = v3_ca
prompt                 = no
input_password         = %(certPassword)s
output_password        = %(certPassword)s

dirstring_type = nobmp

[ req_distinguished_name ]
C = EU
O = StratusLab Project
OU = Testing Department
CN = %(commonName)s

[ v3_ca ]
basicConstraints = CA:false
nsCertType=client, email, objsign
keyUsage=critical, digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment, keyAgreement
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always,issuer:always
subjectAltName=email:%(subjectEmail)s
""" % self.configHolder.options

        conf_filename = os.path.join(self.tmp_dir, 'openssl.cfg')
        open(conf_filename, 'w').write(config)

        Util.printDetail("Generated openssl configuration in: %s" % conf_filename,
                         self.configHolder.verboseLevel)
        Util.printDetail("Openssl configuration: %s" % open(conf_filename).read(),
                         self.configHolder.verboseLevel,
                         Util.VERBOSE_LEVEL_DETAILED)

    def _runCommandsP12(self):
        opts = dict(self.configHolder.options.items() + [('tmp', self.tmp_dir)])

        cmds = []

        cmds.append("openssl genrsa -passout pass:%(certPassword)s -des3 \
-out %(tmp)s/test-key.pem 2048" % opts)

        cmds.append("openssl req -new -key %(tmp)s/test-key.pem \
-out %(tmp)s/test.csr \
-config %(tmp)s/openssl.cfg " % opts)

        cmds.append("openssl x509 -req -days %(certValidity)s \
-in %(tmp)s/test.csr \
-signkey %(tmp)s/test-key.pem \
-out %(tmp)s/test-cert.pem \
-extfile %(tmp)s/openssl.cfg \
-extensions v3_ca \
-passin pass:%(certPassword)s" % opts)

        cmds.append("openssl pkcs12 -export -in %(tmp)s/test-cert.pem \
-inkey %(tmp)s/test-key.pem \
-out %(outputFile)s \
-passin pass:%(certPassword)s \
-passout pass:%(certPassword)s" % opts)

        for cmd in cmds:
            self._runCommand(cmd)

    def _runCommand(self, cmd):
        Util.printDetail('Running: %s' % cmd, self.configHolder.verboseLevel)
        rc, output = commands.getstatusoutput(cmd)
        if rc != 0:
            raise ExecutionException('Failed running %s:\n%s' % (cmd, output))
