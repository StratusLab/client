#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, Centre National de la Recherche Scientifique (CNRS)
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
import urllib2
sys.path.append('/var/lib/stratuslab/python')

# initialize console logging
#import stratuslab.api.LogUtil as LogUtil
#from stratuslab.ConfigHolder import ConfigHolder
#from stratuslab.CommandBase import CommandBaseUser
#from stratuslab.Exceptions import InputException
import stratuslab.Util as Util

#from stratuslab.marketplace import *
#from stratuslab.marketplace.Util import Util as MarketplaceUtil
#from stratuslab.Util import etree_from_text

from stratuslab import Defaults
#from stratuslab.Exceptions import ValidationException

# initialize console logging
import stratuslab.api.LogUtil as LogUtil

LogUtil.get_console_logger()

# define some vars
ENVVAR_ENDPOINT = 'STRATUSLAB_MARKETPLACE_ENDPOINT'
#OPTION_STRING = '--marketplace-endpoint'

ENDPOINT = Defaults.marketplaceEndpoint
ENDPOINT_MKP = ENDPOINT + "/marketplace/metadata"

DCTERMS = "http://purl.org/dc/terms/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
SLTERMS = "http://mp.stratuslab.eu/slterms#"


def MainProgram():
    """
    List images on a given MarketPlace using mechanize
    """

    # checking marketplace endpoint URL
    url_is_ok = Util.checkUrlExists(ENDPOINT_MKP, 30)
    if url_is_ok is True:

        req = urllib2.Request(ENDPOINT_MKP)
        response = urllib2.urlopen(req)
        content = response.read()

        xml = Util.etree_from_text(content)

        desc_nodes = xml.iter("{" + RDF + "}Description")
        all_desc = []
        desc = {}

        for desc_node in desc_nodes:
            desc["description"] = desc_node.find('{' + DCTERMS + '}description').text
            desc["identifier"] = desc_node.find('{' + DCTERMS + '}identifier').text
            desc["creator"] = desc_node.find('{' + DCTERMS + '}creator').text
            desc["created"] = desc_node.find('{' + DCTERMS + '}created').text
            desc["os"] = desc_node.find('{' + SLTERMS + '}os').text
            desc["os-version"] = desc_node.find('{' + SLTERMS + '}os-version').text
            desc["os-arch"] = desc_node.find('{' + SLTERMS + '}os-arch').text

            # cast in str for NoneType object (otherwise, we should use try/Except)
            print "Description: " + str(desc["description"])
            print "ID: " + str(desc["identifier"])
            print "OS: " + str(desc["os"]), str(desc["os-version"]), "| Arch: " + str(desc["os-arch"])
            print "Creator: " + str(desc["creator"])
            print "Created at: " + str(desc["created"].replace("Z", "").split('T'))
            print "####\n"
            all_desc.append(desc)


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
