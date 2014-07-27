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
from optparse import OptionParser
sys.path.append('/var/lib/stratuslab/python')

import stratuslab.Util as Util

from stratuslab import Defaults

from stratuslab.Util import printError
from stratuslab.commandbase.CommandBase import CommandBaseUser

ENVVAR_ENDPOINT = 'STRATUSLAB_MARKETPLACE_ENDPOINT'
#OPTION_STRING = '--marketplace-endpoint'

ENDPOINT = Defaults.marketplaceEndpoint
ENDPOINT_MKP = ENDPOINT + "/marketplace/metadata"

DCTERMS = "http://purl.org/dc/terms/"
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
SLTERMS = "http://mp.stratuslab.eu/slterms#"
SLREQ = "http://mp.stratuslab.eu/slreq#"


class MainProgram(CommandBaseUser):
    """
    Show specific image on a given MarketPlace using mechanize
    """

    def __init__(self):
        self.args = None
        super(MainProgram, self).__init__()

    def parse(self):

        self.parser.usage = '%prog [options] image-id'
        self.parser.description = 'Show a specific image on MarketPlace.'

        self.options, self.args = self.parser.parse_args()

    def checkOptions(self):
        if len(self.args) == 0:
            self.parser.error('Specify image to show')
        if len(self.args) > 1:
            self.parser.error('Only specify one image to show')

        self.options.image = self.args[0]

    def doWork(self):

        id = self.options.image

        # checking marketplace endpoint URL
        url_is_ok = Util.checkUrlExists(ENDPOINT_MKP, 30)
        if url_is_ok is True and id is not False:

            req = urllib2.Request(ENDPOINT_MKP)
            response = urllib2.urlopen(req)
            content = response.read()

            xml = Util.etree_from_text(content)

            desc_nodes = xml.iter("{" + RDF + "}Description")
            desc = {}

            for desc_node in desc_nodes:
                desc["identifier"] = desc_node.find('{' + DCTERMS + '}identifier').text
                if id == desc["identifier"]:

                    desc["checksum"] = {}
                    desc["checksum"]["val"] = []
                    desc["checksum"]["algo"] = []

                    desc["description"] = desc_node.find('{' + DCTERMS + '}description').text
                    desc["creator"] = desc_node.find('{' + DCTERMS + '}creator').text
                    desc["created"] = desc_node.find('{' + DCTERMS + '}created').text
                    desc["valid"] = desc_node.find('{' + DCTERMS + '}valid').text
                    desc["os"] = desc_node.find('{' + SLTERMS + '}os').text
                    desc["os-version"] = desc_node.find('{' + SLTERMS + '}os-version').text
                    desc["os-arch"] = desc_node.find('{' + SLTERMS + '}os-arch').text
                    desc["version"] = desc_node.find('{' + SLTERMS + '}version').text
                    desc["compression"] = desc_node.find('{' + DCTERMS + '}compression').text
                    desc["location"] = desc_node.find('{' + SLTERMS + '}location').text
                    desc["location"] = desc_node.find('{' + SLTERMS + '}location').text
                    desc["format"] = desc_node.find('{' + DCTERMS + '}format').text
                    desc["publisher"] = desc_node.find('{' + DCTERMS + '}publisher').text
                    desc["hypervisor"] = desc_node.find('{' + SLTERMS + '}hypervisor').text
                    for check in desc_node.findall('{' + SLREQ + '}checksum'):
                        desc["checksum"]["algo"].append(check.find('{' + SLREQ + '}algorithm').text)
                        desc["checksum"]["val"].append(check.find('{' + SLREQ + '}value').text)
                    for endorsement in desc_node.findall('{' + SLREQ + '}endorsement'):
                        for endorser in endorsement.findall('{' + SLREQ + '}endorser'):
                            desc["email"] = endorser.find('{' + SLREQ + '}email').text

                    # cast in str for None object (otherwise, I should use try/Except)
                    print "Description: " + str(desc["description"])
                    print "ID: " + str(desc["identifier"])
                    print "Creator: " + str(desc["creator"])
                    print "Created at: " + str(desc["created"].replace("Z", "").split('T'))
                    print "Validity: " + str(desc["valid"].replace("Z", "").split('T'))
                    print "OS: " + str(desc["os"]), str(desc["os-version"]), "| Arch: " + str(desc["os-arch"])
                    print "Version: " + str(desc["version"])
                    print "Compression: " + str(desc["compression"])
                    print "Location: " + str(desc["location"])
                    print "Format: " + str(desc["format"])
                    print "Publisher: " + str(desc["publisher"])
                    print "Hypervisor: " + str(desc["hypervisor"])
                    print "Endorser: " + str(desc["email"])
                    for i in range(len(desc["checksum"]["algo"])):
                        print str(desc["checksum"]["algo"][i]), str(desc["checksum"]["val"][i])
                    print "####\n"


def main():
    try:
        MainProgram()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'
    return 0
