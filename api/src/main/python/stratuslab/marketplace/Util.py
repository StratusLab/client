#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Centre National de la Recherche Scientifique (CNRS)
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
import re

from stratuslab import Defaults
import stratuslab.Util
from stratuslab.Exceptions import ValidationException

class Util(object):

    ENVVAR_ENDPOINT = 'STRATUSLAB_MARKETPLACE_ENDPOINT'

    OPTION_STRING = '--marketplace-endpoint'

    @staticmethod
    def addEndpointOption(parser):
        default = os.getenv(Util.ENVVAR_ENDPOINT,
                            Defaults.marketplaceEndpoint)
        parser.add_option(Util.OPTION_STRING,
                          dest='marketplaceEndpoint',
                          help='Marketplace endpoint (hostname or URL). Default %s or %s' % \
                              (Util.ENVVAR_ENDPOINT,
                               Defaults.marketplaceEndpoint),
                          default=default)

        
    @staticmethod
    def checkEndpointOption(options):
        if not options.marketplaceEndpoint:
            options.marketplaceEndpoint = os.getenv(Util.ENVVAR_ENDPOINT,
                                                    Defaults.marketplaceEndpoint)

        options.marketplaceEndpoint = re.sub(r"/*$", '', options.marketplaceEndpoint)

        return True

    @staticmethod
    def metadataUrl(endpoint, identifier):
        if identifier.startswith('http'):
            return identifier
        
        if not endpoint:
            raise ValidationException('Marketplace endpoint is not provided ' +\
                                      'when building metadata URL.')

        _endpoint = stratuslab.Util.sanitizeEndpoint(endpoint, 
                                                     Defaults.marketplaceProtocol,
                                                     Defaults.marketplacePort)
        return '%s/metadata/%s' % (_endpoint, identifier)

    @staticmethod
    def metadataCompleteUrl(endpoint, identifier, email, created):
        return '%s/metadata/%s/%s/%s' % (endpoint, identifier, email, created)

    @staticmethod
    def metadataEndpointUrl(endpoint):
        return '%s/metadata' % endpoint
