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
import sys
import os.path
import urllib2
from ConfigParser import RawConfigParser

import Util
from ManifestInfo import ManifestInfo
from Exceptions import InputException
from Exceptions import NetworkException
from Signator import Signator
from ConfigHolder import ConfigHolder

import marketplace.Downloader
import marketplace.Uploader


try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise Exception("Failed to import ElementTree from any known place")


class Uploader(object):

    MARKETPLACE_ADDRESS = 'STRATUSLAB_MARKETPLACE_ENDPOINT'

    @staticmethod
    def availableCompressionFormat(printIt=False):
        list = ('gz', 'bz2') # TODO: refactor - move out from here

        if printIt:
            print 'Available compression format: %s' % ', '.join(list)
            sys.exit(0)
        else:
            return list

    @staticmethod
    def buildUploadParser(parser):
        parser.usage = '''usage: %prog [options] <metadata-file>'''

        parser.add_option('-r', '--repository', dest='appRepoUrl',
                help='appliance repository address. Default STRATUSLAB_REPO_ADDRESS',
                default=os.getenv('STRATUSLAB_REPO_ADDRESS'), metavar='ADDRESS')

        parser.add_option('--curl-option', dest='uploadOption', metavar='OPTION',
                help='additional curl option', default='')

        parser.add_option('-C', '--compress', dest='compressionFormat',
                help='compression format',
                default='gz', metavar='FORMAT')
        parser.add_option('-f', '--force', dest='forceUpload',
                help='force upload of the appliance even if already exists',
                default=False, action='store_true')

        parser.add_option('--list-compression', dest='listCompressionFormat',
                help='list available compression formats',
                default=False, action='store_true')

        parser.add_option('--with-marketplace', dest='withMarketPlace',
                help='Also upload the metadata file to the marketplace',
                default=False, action='store_true')

        parser.add_option('--marketplace-endpoint', dest='marketPlaceEndpoint',
                help='Market place endpoint. Default %s or %s' % (Uploader.MARKETPLACE_ADDRESS, marketplace.Downloader.Downloader.ENDPOINT),
                default=None)

        parser.add_option('--marketplace-only', dest='withMarketPlaceOnly',
                help='Only upload the metadata file to the marketplace, don\'t upload the image to the appliances repository',
                action='store_true',
                default=False)

        parser.add_option('-U', '--repo-username', dest='repoUsername',
                help='repository username. Default STRATUSLAB_REPO_USERNAME',
                default=os.getenv('STRATUSLAB_REPO_USERNAME'))
        parser.add_option('-P', '--repo-password', dest='repoPassword',
                help='repository password. Default STRATUSLAB_REPO_PASSWORD',
                default=os.getenv('STRATUSLAB_REPO_PASSWORD'))

    @staticmethod
    def checkUploadOptions(options, parser):

        if options.marketPlaceEndpoint:
            options.withMarketPlace = True
        if not options.marketPlaceEndpoint:
            options.marketPlaceEndpoint = os.getenv(Uploader.MARKETPLACE_ADDRESS, marketplace.Downloader.Downloader.ENDPOINT)                    

        if options.withMarketPlaceOnly:
            options.withMarketPlace = True
            return

        if options.compressionFormat not in Uploader.availableCompressionFormat():
            parser.error('Unknown compression format')
        if not options.appRepoUrl:
            parser.error('Unspecified repository address')
        if not options.repoUsername:
            parser.error('Unspecified repository username')
        if not options.repoPassword:
            parser.error('Unspecified repository password')
 
    @staticmethod
    def buildRepoNameStructure(structure, info):
        varPattern = '#%s#'
        dirVarPattern = '#%s_#'
        for part in ('type', 'os', 'arch', 'version', 'osversion', 'compression'):
            if structure.find(varPattern % part) != -1:
                structure = structure.replace(varPattern % part, getattr(info, part))

            if structure.find(dirVarPattern % part) != -1:
                structure = structure.replace(dirVarPattern % part, getattr(info, part).replace('.', '/'))
        return structure

    def __init__(self, manifestFile, configHolder=ConfigHolder()):
        self.configHolder = configHolder
        configHolder.assign(self)
        self.manifestFile = manifestFile
        self.appliance = self.manifestFile.replace('.xml', '.img')
        self.curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.repoUsername,
                                                             self.repoPassword)]
        self.uploadedFile = []

        self.os = ''
        self.osversion = ''
        self.arch = ''
        self.type = ''
        self.version = ''
        self.compression = ''
        self.repoStructure = ''
        self.repoFilename = ''

        if not hasattr(self, 'remoteImage'):
            self.remoteImage = False

        self.remoteServerAddress = None

    def start(self):
        Util.printAction('Starting appliance upload')

        if not self.withMarketPlaceOnly:
            Util.printStep('Compressing appliance')
            self._compressAppliance()

        Util.printStep('Parsing manifest')
        self._parseManifestAndSetObjectAttributes()

        if not self.withMarketPlaceOnly:
            Util.printStep('Parsing repository configuration')
            self._parseRepoConfig()

            Util.printStep('Uploading appliance')
            self._uploadAppliance()

            Util.printStep('Signing manifest')
            self._signManifest()

            Util.printStep('Uploading manifest')
            self._uploadManifest()
        
        if self.withMarketPlace:
            self._uploadMarketPlaceManifest()

        Util.printAction('Appliance uploaded successfully')
        print '\n\t%s' % '\n\t'.join(self.uploadedFile)

    def _uploadAppliance(self):
        applianceUri = '%s/%s' % (self.repoStructure, self.repoFilename)
        if self.remoteImage:
            self.uploadFileFromRemoteServer(self.appliance, applianceUri)
        else:
            self.uploadFile(self.appliance, applianceUri)

        self._addLocationToManifest('%s/%s' % (self.appRepoUrl, applianceUri))

    def _signManifest(self):
        configHolder = ConfigHolder(self.__dict__)
        signator = Signator(self.manifestFile, configHolder)
        signator.sign()
        self.manifestFile = signator.outputManifestFile

    def _uploadManifest(self):
        repoFilename = self.repoFilename.replace('img.%s' % self.compression, 'xml')
        self.uploadFile(self.manifestFile, '%s/%s' % (self.repoStructure,
                                                      repoFilename))

    def uploadFileFromRemoteServer(self, filename, remoteName):
        self.uploadFile(filename, remoteName, remoteServer=True)

    def uploadFile(self, filename, remoteName, remoteServer=False):
        if Util.getProtoFromUri(remoteName) and Util.getHostnameFromUri(remoteName):
            uploadUrl = remoteName
        else:
            uploadUrl = '%s/%s' % (self.appRepoUrl, remoteName)

        curlUploadCmd = self.curlCmd + ['-T', filename]

        self._checkFileAlreadyExists(remoteName)
        self._createRemoteDirectoryStructure(os.path.dirname(uploadUrl))

        if self.uploadOption:
            curlUploadCmd.append(self.uploadOption)

        curlUploadCmd.append(uploadUrl)
        if remoteServer:
            strCurlUploadCmd = ' '.join(curlUploadCmd)
            ret = Util.sshCmd(strCurlUploadCmd, self.remoteServerAddress,
                         sshKey=self.userPrivateKeyFile,
                         verboseLevel=self.verboseLevel,
                         verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
        else:
            devNull = self._openDevNull()
            ret = Util.execute(curlUploadCmd, stdout=devNull, stderr=devNull,
                          verboseLevel=self.verboseLevel,
                          verboseThreshold=Util.DETAILED_VERBOSE_LEVEL)
            devNull.close()

        if ret != 0:
            raise NetworkException('An error occurred while uploading %s' % uploadUrl)

        self.uploadedFile.append(uploadUrl)

    def _openDevNull(self):
        return open('/dev/null', 'w')

    def _execute(self, command):
        if self.verboseLevel <= Util.NORMAL_VERBOSE_LEVEL:
            devNull = open('/dev/null', 'w')
            ret = Util.execute(command, stdout=devNull, stderr=devNull)
            devNull.close()
        else:
            ret = Util.execute(command)
        return ret

    def deleteFile(self, url):
        deleteCmd = self.curlCmd + [ '-X', 'DELETE', url]
        self._execute(deleteCmd)

    def deleteDirectory(self, url):
        if not url.endswith('/'):
            url += '/'
        self.deleteFile(url)

    def _getDirectoriesOfUrl(self, url):
        urlDirs = '/'.join(url.split('//')[1:])
        newDirs = ['']
        for dir in urlDirs.split('/')[1:]:
            newDirs.append('%s%s/' % (newDirs[-1], dir))

        return newDirs[1:]

    def _createRemoteDirectoryStructure(self, url):
        curlCreateDirCmd = self.curlCmd + ['-X', 'MKCOL']
        urlDirs = self._getDirectoriesOfUrl(url)
        repoAddress = '/'.join(url.split('/')[0:3])

        for dir in urlDirs:
            if dir == '':
                continue
            curlCreateDirCmd.append('%s/%s' % (repoAddress, dir))
            self._execute(curlCreateDirCmd)
            curlCreateDirCmd.pop()

    def _checkFileAlreadyExists(self, filename):
        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None, self.appRepoUrl, self.repoUsername, self.repoPassword)

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        status = 0
        try:
            opener.open('%s/%s' % (self.appRepoUrl, filename))
        except urllib2.HTTPError, e:
            status = e.code

        if status != 404 and not self.forceUpload:
            raise InputException('An appliance already exist at this URL.\n'
                       'Change the appliance version or force upload with '
                       '-f --force option')

    def _parseManifestAndSetObjectAttributes(self):
        manifestInfo = ManifestInfo()
        manifestInfo.parseManifestFromFile(self.manifestFile)
        attrList = ['os', 'osversion', 'arch', 'type', 'version', 'compression']
        for attr in attrList:
            setattr(self, attr, getattr(manifestInfo, attr))

    def _parseRepoConfig(self):
        tmpRepoCfg = '/tmp/stratus-repo.tmp'
        Util.wget('%s/%s' % (self.appRepoUrl, Util.defaultRepoConfigPath), tmpRepoCfg)

        repoConf = RawConfigParser()
        repoConf.read(tmpRepoCfg)
        os.remove(tmpRepoCfg)

        repoStructure = repoConf.get(Util.defaultRepoConfigSection, 'repo_structure')
        repoFilename = repoConf.get(Util.defaultRepoConfigSection, 'repo_filename')

        self.repoStructure = self.buildRepoNameStructure(repoStructure, self)
        # compression is a special case
        if not self.compression:
            self.compression = self.compressionFormat
        self.repoFilename = self.buildRepoNameStructure(repoFilename, self)

    def _buildManifestName(self, repoFilename):
        return repoFilename.split('.img')[0] + '.xml'

    def _compressFile(self, file, format):
        # TODO: use stratuslab.Compressor
        if format == 'gz':
            compressionCmd = 'gzip'
        elif format == 'bz2':
            compressionCmd = 'bzip2'
        else:
            raise NotImplementedError('Unknown compression format')

        compressedFilename = '%s.%s' % (file, format)
        if os.path.isfile(compressedFilename):
            Util.printWarning('Compressed file %s already exists, skipping' % compressedFilename)
            return compressedFilename

        if not os.path.exists(file):
            Util.printError('Missing file: ' + file, exit=True)

        ret = self._execute([compressionCmd, file])
        if ret != 0:
            Util.printError('Error compressing file: ' % compressedFilename, exit=True)

        return compressedFilename

    def _compressAppliance(self):
        self.appliance = self._compressFile(self.appliance, self.compressionFormat)
        self._addCompressionFormatToManifest()

    def _addCompressionFormatToManifest(self):
        # TODO: extract _addToManifest()
        xml = etree.ElementTree()
        docElement = xml.parse(self.manifestFile)

        compressionElem = xml.find('.//{%s}compression' % ManifestInfo.NS_DCTERMS)
        if compressionElem and compressionElem.text != None:
            Util.printWarning("compression already defined in the manifest file with value: " + compressionElem.text)
        else:
            compressionElem = etree.Element('{%s}compression' % ManifestInfo.NS_DCTERMS)
            descriptionElement = docElement.find('.//{%s}Description' % ManifestInfo.NS_RDF)
            descriptionElement.append(compressionElem)

        compressionElem.text = self.compressionFormat
        xml.write(self.manifestFile)

    def _addLocationToManifest(self, applianceUri):
        # TODO: extract _addToManifest()
        xml = etree.ElementTree()
        docElement = xml.parse(self.manifestFile)

        locationElem = xml.find('.//{%s}location' % ManifestInfo.NS_SLTERMS)

        if locationElem and locationElem.text != None:
            Util.printWarning("<location> already defined in the manifest file with value: " +
                        locationElem.text)
        else:
            locationElem = etree.Element('{%s}location' % ManifestInfo.NS_SLTERMS)
            descriptionElement = docElement.find('.//{%s}Description' % ManifestInfo.NS_RDF)
            descriptionElement.append(locationElem)

        locationElem.text = applianceUri
        xml.write(self.manifestFile)

    def _uploadMarketPlaceManifest(self):
        uploader = marketplace.Uploader.Uploader(self.configHolder)
        uploader.upload(self.manifestFile)
        
