#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2012, SixSq Sarl
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
import time

import stratuslab.system.SystemFactory as SystemFactory
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.installator.Installator import Installator
from stratuslab.Util import appendOrReplaceInFile, service, filePutContent,\
    printWarning, printError

class Sunstone(Installator):
    def __init__(self, configHolder=ConfigHolder()):

        self.configHolder = configHolder
        self.configHolder.assign(self)

        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        
        self.packages = ['lighttpd', 'rubygem-json', 'ruby-sqlite3']
        self.ruby_gems = ['sinatra']

        self.sunstone_cfg = '/etc/one/sunstone-server.conf'
        self.lighttpd_cfg = '/etc/lighttpd/lighttpd.conf'
        self.lighttpd_cert = '/etc/lighttpd/server.pem'

    def _installFrontend(self):
        self._installPackages()
        self._installRubyGems()

    def _installPackages(self):
        self.system.installPackages(self.packages)

    def _installRubyGems(self):
        cmd = ['gem', 'install', '--no-rdoc', '--no-ri'] + self.ruby_gems 
        rc, output = self.system.executeCmdWithOutput(cmd)
        if rc != 0:
            printError("Failed to install Ruby gems: %s" % output)

    def _setupFrontend(self):
        self._updateSunstoneConfig()
        self._configureSslProxy()

    def _updateSunstoneConfig(self):
        appendOrReplaceInFile(self.sunstone_cfg,
                              ':port:', ':port: %s' % self.sunstonePort)

    def _configureSslProxy(self):
        self._setupSslProxyCert()
        self._enableSslProxy()
        self._setFirewallRules()

    def _setupSslProxyCert(self):
        if self.sunstoneSslProxyCert:
            self.lighttpd_cert = self.sunstoneSslProxyCert
        else:
            dummy_cert = """
-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDQCc1NmyEZgk6u
NsZo2o8gSEGG3uANugp/TPX5BRQ/sxzPaU7tMZ9Ige567icPUWQjQG8lZiGbIL+q
m8zt3ezBNwS4LH+7OfzjISeJ8y2lo/Xdk9UUlVcBnibPYJdzh25pBXNSHBp9FAzu
GFvv2XKpY1RzGLGuE0kr4EC6Sou/Jch/NnryCEQUt5OCrzqd+qGEJxDuuTnx0uqt
8XoTULXnZuSz+v1iz31QRRomofk7POQFBLkcU1TCAfX7q1qM6/sYDxppyZHUr8PA
PAEn6M+j33HnotzyR3AkcQV+HL1XO3sC8ZM5Q7WG5md3mflgJq364wSWFPhnyt9v
y53gxtHbAgMBAAECggEAAYyRIsrM7Eu0Gkf+Ijm+ZxcipcZzFKcV/OytyDTpea/z
vvehxtJfxUJybCfp0otgm4KXUUf5aBZOVw7h78N/R9EJD/YE3XgJEgflK3nMFTer
VQMMyyJxi2mKEHE/r3SKte18dlgPOm8zyXIU/Sw5VlmO/2xnpkwud00sLjbv43R5
IeMQlptho5g+Nqo6VGODLC7xp6GXI2gBDMF89R5tgtbT9RvzpkyHyfBuW5M18k+P
PqCaY7rB3a+WCK7PJrd6pawo3RMzzTmglIl0TJCIcT25aRK1DC97utN2YdwSIuNo
RehwxsdC1KHF+Gj21BaBXRyj9IdVH26D1T5bp/6ggQKBgQDnOOF2cbrfjNeC+yyR
ooB/7xyuPmUW0XPyrKqp5LOKaOnHEhe7CrU/o3ZDdZ9NFzvsM+gFNq7E0aF07Xjq
xmkPjUZuub4SGABW9jr7DwW9FqZGoTtbDdL7TBP+ogEzJshTFH6bXNidO0SxfTUp
V7k1jpvPJdQZpXoXKdEHPow9YwKBgQDmVOrNERrnKo9g1wQ8l+NHgySzLIcks7TD
Jbc51LT4eAQKx7SyeZTy79cTimrK0WCtOhwrVEEaMsNGKQiOc0ulsS4o8Q88XYJp
ji6/ys+os/ShagPFnu40rtHmsNp+JSX04XwNQR61uocqV0fVxq3CEP9OAWn4lnCk
ulZxujYfKQKBgQCGK7aA8Xu7rtF7mt6A36frFMgyv9gPBplejx01GpWoUjqdnn0Q
tyT3eZXtjTpUFJBb/r67D8EYSoCDBi2tJlbehF8Db1rAyxafX6BYAJ6W26a+w15a
9smfssTDdCR4FyAVPYY+BwFXM4Yn6/zGMbYyQr9c05mhDCmteUFnD792+wKBgQDD
kORQO67JCkT053vMavZqOLqHe04/5mmbrEFXU/hYY6ai9I/DXiIO53+JMuSb0o0w
Z/+U9pPUR7evsZV3RgO76qWT06GpEohxUWz2IaCR0EHsb5RGTjxY9Pp50j2iD66b
rnxi0KDfkkHDvJnctDXCaiYruF2e2TVJWIGfTIk5iQKBgQDJkPpctI3IhltSIOVL
1wpv91/4m2JO59lfesTTCsMMW/lU4ayPJrELYdfrIog3hXuWPFF87VQyO5veiJwy
ne55hCx/OA5aubHO7w5fXaoO65BbusVLoK0W9NlIzuNXpK+v69b/eb2xofgkbgy9
oFBWR9WnQVZpbC4FR6QsKNY0Qw==
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIICvjCCAaYCCQDLhOmFHE0zYDANBgkqhkiG9w0BAQUFADAhMR8wHQYDVQQDExZv
bmV2bS05Ni5zdHJhdHVzbGFiLmV1MB4XDTEyMDQxMDIyMTAxMFoXDTIyMDQwODIy
MTAxMFowITEfMB0GA1UEAxMWb25ldm0tOTYuc3RyYXR1c2xhYi5ldTCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBANAJzU2bIRmCTq42xmjajyBIQYbe4A26
Cn9M9fkFFD+zHM9pTu0xn0iB7nruJw9RZCNAbyVmIZsgv6qbzO3d7ME3BLgsf7s5
/OMhJ4nzLaWj9d2T1RSVVwGeJs9gl3OHbmkFc1IcGn0UDO4YW+/ZcqljVHMYsa4T
SSvgQLpKi78lyH82evIIRBS3k4KvOp36oYQnEO65OfHS6q3xehNQtedm5LP6/WLP
fVBFGiah+Ts85AUEuRxTVMIB9furWozr+xgPGmnJkdSvw8A8ASfoz6Pfceei3PJH
cCRxBX4cvVc7ewLxkzlDtYbmZ3eZ+WAmrfrjBJYU+GfK32/LneDG0dsCAwEAATAN
BgkqhkiG9w0BAQUFAAOCAQEAwTIyerWZXfcDTaNwqxy59JzHm+v0UqZqKxQ2wYh2
PHGx19qA41W7trm7BlxaSwaq7iskcwgfhmmd2kXur9rs58rALDbAv7MRCQ7xfjb2
oAPTQTar2UVC4yxzeEYU7NGdqkPUC0/HeMstVdYX8W0B9UyuokjU0FAibPzFLaSu
eEIH1OTZu9Il2Co3X5ClDgc3Q/LjVQFNqhpJyUIu00tKB2nfDXrbco8L/7Q4NIJu
gxkHOHYxOMO7tclnJR3HX+8HogcWHSqPTMgJYX+ihM0E5X5lm9cWBUeAseNPasy6
3AxkYyyBEKMOcZTehs7kwvFWajUBFkvPgI3a6GsfCX5VpA==
-----END CERTIFICATE-----
"""
            filePutContent(self.lighttpd_cert, dummy_cert, neverShowData=True)
            os.chmod(self.lighttpd_cert, 0600)

        appendOrReplaceInFile(self.lighttpd_cfg, 'ssl.pemfile', 
                                   'ssl.pemfile = "%s"' % self.lighttpd_cert)

    def _enableSslProxy(self):
        appendOrReplaceInFile(self.lighttpd_cfg, 'ssl.engine',
                                   'ssl.engine = "enable"')

        appendOrReplaceInFile(self.lighttpd_cfg, 'server.port', 
                                   'server.port = %s' % self.sunstoneSslProxyPort)

        sunstone_proxy_cfg = '/etc/lighttpd/conf.d/sunstone-proxy.conf'
        conf = """
    server.modules += ("mod_alias")
    server.modules += ("mod_proxy")
    server.modules += ("mod_compress")
    proxy.server = ("" => ( "" => ( "host" => "127.0.0.1", "port" => %s ) ) )
    """ % self.sunstonePort
        filePutContent(sunstone_proxy_cfg, conf)

    def _setFirewallRules(self):
        rules = ({'table':'filter',
                  'rule' :'-A INPUT -s 127.0.0.1 -p tcp -m tcp --dport %s -j ACCEPT' % self.sunstonePort},
                 {'table':'filter',
                  'rule' :'-A INPUT -p tcp -m tcp --dport %s -j REJECT --reject-with icmp-port-unreachable' % self.sunstonePort})

        if not self.system._isSetFirewallRulesAll(rules):
            self.system._setFirewallRulesAll(rules)
            self.system._persistFirewallRules()

    def _startServicesFrontend(self):
        self._restartSunstone()
        self._restartSslProxy()

    def _restartSunstone(self):
        self._stopSunstone()
        time.sleep(2)
        self._startSunstone()

    def _startSunstone(self):
        self._sunstoneService('start')

    def _stopSunstone(self):
        self._sunstoneService('stop')

    def _sunstoneService(self, action):
        cmd = 'su - %s -c "sunstone-server %s"' % (self.oneUsername, action)
        rc, output = self.system.executeCmdWithOutput(cmd, shell=True)
        if rc != 0:
            msg = "Failed to %s sunstone-server: %s" % (action, output)
            if action == 'start':
                printError(msg)
            else:
                printWarning(msg)

    def _restartSslProxy(self):
        self.system.executeCmd(['chkconfig', 'lighttpd', 'on'])
        service('lighttpd', 'restart')
