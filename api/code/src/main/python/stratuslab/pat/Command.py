#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552.
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique
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

import sys

from stratuslab import Util
from stratuslab.CommandBase import CommandBaseUser

class PortTranslationCommand(CommandBaseUser):

    @staticmethod
    def addCommonOptions(parser):
        parser.add_option('--pat-enable', dest='portTranslation',
                help='show port address translations',
                action='store_true', default=False)

        parser.add_option('--pat-service-host', dest='patServiceHost',
                help='set the hostname/ip of port translation service',
                action='store', metavar='HOST/IP')

        parser.add_option('--pat-gateway-host', dest='patGatewayHost',
                help='set the hostname/ip of port translation gateway',
                action='store', metavar='HOST/IP')

    def checkCommonOptions(self):
        self.checkServiceHost()
        self.checkGatewayHost()

    def checkServiceHost(self):
        self._setOptionIfNotDefined('patServiceHost', self.options.endpoint)

    def checkGatewayHost(self):
        self._setOptionIfNotDefined('patGatewayHost', self.options.endpoint)

    def _setOptionIfNotDefined(self, option, default):
        if not getattr(self.options, option, None):
            if self.verboseLevel >= Util.VERBOSE_LEVEL_NORMAL:
                sys.stdout.write("Warning: '%s' is not defined, using '%s'.\n" % (option, default))
            setattr(self.options, option, default)

