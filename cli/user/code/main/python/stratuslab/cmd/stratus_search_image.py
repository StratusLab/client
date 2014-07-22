#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, Centre National de la Recherche Scientifique (CNRS)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys
import urllib2
import re
from optparse import OptionParser

sys.path.append('/var/lib/stratuslab/python')

import stratuslab.Util as Util
# from stratuslab.marketplace.Util import Util as MarketplaceUtil
# from stratuslab.Util import etree_from_text

from stratuslab import Defaults
# from stratuslab.Exceptions import ValidationException

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
SLREQ = "http://mp.stratuslab.eu/slreq#"


def MainProgram():
    """
    Search specific image on a given MarketPlace using mechanize
    """

    parser = OptionParser()

    parser.usage = '%prog [options]...'
    parser.description = 'Search a specific image on MarketPlace.'

    parser.add_option("-c", "--creator",
                      action="store", type="string", dest="creator")
    parser.add_option("-e", "--email",
                      action="store", type="string", dest="email")
    parser.add_option("--os",
                      action="store", type="string", dest="os")
    parser.add_option("-d", "--description",
                      action="store", type="string", dest="description")
    parser.add_option("--description_regexp",
                      action="store", type="string", dest="regexp")
    parser.add_option("-a", "--arch",
                      action="store", type="string", dest="arch")

    (options, args) = parser.parse_args()

    if not options.creator and not options.email and not options.os and \
            not options.description and not options.regexp and not options.arch:
        parser.error('Please specify something to search')

    key_criteria = {"creator": "",
                    "email": "",
                    "os": "",
                    "description": "",
                    "regexp": "",
                    "arch": ""}

    use_regexp = False

    if options.creator is not None:
        creator = options.creator
        key_criteria["creator"] = creator
    if options.email is not None:
        email = options.email
        key_criteria["email"] = email
    if options.os is not None:
        os = options.os
        key_criteria["os"] = os
    if options.description is not None:
        description = options.description
        key_criteria["description"] = description
    description_compile = None
    if options.regexp is not None:
        regexp = options.regexp
        use_regexp = True
        key_criteria["description"] = regexp
        description_compile = re.compile(regexp)
    if options.arch is not None:
        arch = options.arch
        key_criteria["arch"] = arch

    # checking marketplace endpoint URL
    url_is_ok = Util.checkUrlExists(ENDPOINT_MKP, 30)
    if url_is_ok is True:

        req = urllib2.Request(ENDPOINT_MKP)
        response = urllib2.urlopen(req)
        content = response.read()

        xml = Util.etree_from_text(content)

        desc_nodes = xml.iter("{" + RDF + "}Description")
        desc = {}

        found = 0

        for desc_node in desc_nodes:

            if key_criteria["creator"] != "":
                desc["creator"] = desc_node.find('{' + DCTERMS + '}creator').text
                if key_criteria["creator"] == desc["creator"]:
                    if found < 1:
                        print "####"
                    found += 1
                    print "CREATOR FOUND"

            if key_criteria["os"] != "":
                desc["os"] = desc_node.find('{' + SLTERMS + '}os').text
                if key_criteria["os"] == desc["os"]:
                    if found < 1:
                        print "####"
                    found += 1
                    print "OS FOUND"

            if key_criteria["arch"] != "":
                desc["arch"] = desc_node.find('{' + SLTERMS + '}os-arch').text
                if key_criteria["arch"] == desc["arch"]:
                    if found < 1:
                        print "####"
                    found += 1
                    print "ARCH FOUND"

            if key_criteria["description"] != "":
                desc["description"] = desc_node.find('{' + DCTERMS + '}description').text
                if use_regexp is False:
                    if key_criteria["description"] == desc["description"]:
                        if found < 1:
                            print "####"
                        found += 1
                        print "DESCRIPTION FOUND"
                else:
                    if desc["description"] is not None and description_compile is not None:
                        if description_compile.search(desc["description"]):
                            if found < 1:
                                print "####"
                            found += 1
                            print "DESCRIPTION[REGEXP] FOUND"

            if key_criteria["email"] != "":
                for endorsement in desc_node.findall('{' + SLREQ + '}endorsement'):
                    for endorser in endorsement.findall('{' + SLREQ + '}endorser'):
                        desc["email"] = endorser.find('{' + SLREQ + '}email').text
                if key_criteria["email"] == desc["email"]:
                    if found < 1:
                        print "####"
                    found += 1
                    print "EMAIL FOUND"

            if found >= 1:
                print "%d critera match your search for this image" % found
                print "####"
                print_image(desc_node)

            found = 0


def print_image(desc_node):
    """
    Print a specific image description
    """
    desc = {"checksum": {"val": [],
                         "algo": []},
            "identifier": desc_node.find('{' + DCTERMS + '}identifier').text,
            "description": desc_node.find('{' + DCTERMS + '}description').text,
            "creator": desc_node.find('{' + DCTERMS + '}creator').text,
            "created": desc_node.find('{' + DCTERMS + '}created').text,
            "valid": desc_node.find('{' + DCTERMS + '}valid').text,
            "os": desc_node.find('{' + SLTERMS + '}os').text,
            "os-version": desc_node.find('{' + SLTERMS + '}os-version').text,
            "os-arch": desc_node.find('{' + SLTERMS + '}os-arch').text,
            "version": desc_node.find('{' + SLTERMS + '}version').text,
            "compression": desc_node.find('{' + DCTERMS + '}compression').text,
            "location": desc_node.find('{' + SLTERMS + '}location').text,
            "format": desc_node.find('{' + DCTERMS + '}format').text,
            "publisher": desc_node.find('{' + DCTERMS + '}publisher').text,
            "hypervisor": desc_node.find('{' + SLTERMS + '}hypervisor').text}

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
