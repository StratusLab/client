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
import os.path
import sys
import urllib2
from ConfigParser import RawConfigParser

from stratuslab.Exceptions import NetworkException
from stratuslab.Exceptions import InputException

from stratuslab.Util import assignAttributes
from stratuslab.Util import defaultRepoConfigPath
from stratuslab.Util import defaultRepoConfigSection
from stratuslab.Util import execute
from stratuslab.Util import manifestExt
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import wget

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

    def __init__(self, manifest, options):
        assignAttributes(self, options)
        self.manifest = manifest
        self.appliance = self.manifest.replace(manifestExt, '')        
        self.curlCmd = ['curl', '-k', '-f', '-u', '%s:%s' % (self.repoUsername,
                                                             self.repoPassword)]
        self.uploadedFile = []

        self.os = None
        self.osversion = None
        self.arch = None
        self.type = None
        self.version = None
        self.compression = None
        self.repoStructure = ''
        self.repoFilename = ''

    def start(self):
        printAction('Starting appliance upload')

        printStep('Compressing appliance')
        self._compressAppliance()

        printStep('Parsing manifest')
        self._parseManifest()

        printStep('Parsing repository configuration')
        self._parseRepoConfig()

        printStep('Uploading appliance')
        self._uploadAppliance()

        printStep('Uploading manifest')
        self._uploadManifest()

        printAction('Appliance uploaded successfully')
        print '\n\t%s' % '\n\t'.join(self.uploadedFile)
        
    def _uploadAppliance(self):
        self.uploadFile(self.appliance, '%s/%s' % (self.repoStructure, self.repoFilename))

    def _uploadManifest(self):
        repoFilename = self.repoFilename.replace('.%s' % self.compression, manifestExt)
        self.uploadFile(self.manifest, '%s/%s' % (self.repoStructure, repoFilename))
                                                       
    def uploadFile(self, filename, remoteName):
        uploadUrl = '%s/%s' % (self.repoAddress, remoteName)
        curlUploadCmd = self.curlCmd + ['-T', filename]

        self._checkFileAlreadyExists(remoteName)
        self._createRemoteDirectoryStructure(os.path.dirname(uploadUrl))

        if self.uploadOption:
            curlUploadCmd.append(self.uploadOption)
            
        curlUploadCmd.append(uploadUrl)
        devNull = self._openDevNull()
        ret = execute(curlUploadCmd, stdout=devNull, stderr=devNull)
        devNull.close()
        
        if ret != 0:
            raise NetworkException('An error occurred while uploading %s' % uploadUrl)

        self.uploadedFile.append(uploadUrl)

    def _openDevNull(self):
        return open('/dev/null', 'w')

    def deleteFile(self, url):
        devNull = self._openDevNull()
        deleteCmd = self.curlCmd + [ '-X', 'DELETE', url]
        execute(deleteCmd, stdout = devNull, stderr = devNull)
        devNull.close()

    def _getDirectoriesOfUrl(self, url):
        urlDirs = '/'.join(url.split('//')[1:])
        newDirs = ['']
        for dir in urlDirs.split('/')[1:]:
            newDirs.append('%s%s/' % (newDirs[-1], dir))

        return newDirs[1:]

    def _createRemoteDirectoryStructure(self, url):
        devNull = self._openDevNull()
        curlCreateDirCmd = self.curlCmd + ['-X', 'MKCOL']
        urlDirs = self._getDirectoriesOfUrl(url)
        repoAddress = '/'.join(url.split('/')[0:3])

        for dir in urlDirs:
            if dir == '':
                continue
            curlCreateDirCmd.append('%s/%s' % (repoAddress, dir))
            execute(curlCreateDirCmd, stderr=devNull, stdout=devNull)
            curlCreateDirCmd.pop()
        devNull.close()

    def _checkFileAlreadyExists(self, filename):
        passwordMgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passwordMgr.add_password(None, self.repoAddress, self.repoUsername, self.repoPassword)

        handler = urllib2.HTTPBasicAuthHandler(passwordMgr)
        opener = urllib2.build_opener(handler)

        status = 0
        try:
            opener.open('%s/%s' % (self.repoAddress, filename))
        except urllib2.HTTPError, e:
            status = e.code

        if status != 404 and not self.forceUpload:
            raise InputException('An appliance already exist at this URL.\n'
                       'Change the appliance version of force upload with '
                       '-f --force option')

    def _parseManifest(self):
        xml = etree.ElementTree()
        xml.parse(self.manifest)
        self.os = xml.find('os').text
        self.osversion = xml.find('osversion').text
        self.arch = xml.find('arch').text
        self.type = xml.find('type').text
        self.version = xml.find('version').text
        self.compression = xml.find('compression').text

    def _parseRepoConfig(self):
        tmpRepoCfg = '/tmp/stratus-repo.tmp'
        wget('%s/%s' % (self.repoAddress, defaultRepoConfigPath), tmpRepoCfg)

        repoConf = RawConfigParser()
        repoConf.read(tmpRepoCfg)
        os.remove(tmpRepoCfg)

        repoStructure = repoConf.get(defaultRepoConfigSection, 'repo_structure')
        repoFilename = repoConf.get(defaultRepoConfigSection, 'repo_filename')

        self.repoStructure = self._buildRepoNameStructure(repoStructure)
        self.repoFilename = self._buildRepoNameStructure(repoFilename)

    def _buildRepoNameStructure(self, structure):
        varPattern = '#%s#'
        dirVarPattern = '#%s_#'
        for part in ('type', 'os', 'arch', 'version', 'osversion', 'compression'):
            if structure.find(varPattern % part) != -1:
                structure = structure.replace(varPattern % part, getattr(self, part, ''))

            if structure.find(dirVarPattern % part) != -1:
                structure = structure.replace(dirVarPattern % part, getattr(self, part, '').replace('.', '/'))
        return structure

    def _compressFile(self, file, format):
        if format == 'gz':
            compressionCmd = 'gzip'
        elif format == 'bz2':
            compressionCmd = 'bzip2'
        else:
            raise NotImplementedError('Unknow compression format')

        compressedFilename = '%s.%s' % (file, format)
        if os.path.isfile(compressedFilename):
            printError('Compressed file %s already exists, skipping' % compressedFilename, exit=False)

        devNull = self._openDevNull()
        execute([compressionCmd, file], stderr=devNull, stdout=devNull)
        devNull.close()

        return compressedFilename

    def _compressAppliance(self):
        self.appliance = self._compressFile(self.appliance, self.compressionFormat)
        self._addCompressionFormatToManifest()

    def _addCompressionFormatToManifest(self):
        compressionElem = etree.Element('compression')
        compressionElem.text = self.compressionFormat

        xml = etree.ElementTree()
        manifest = xml.parse(self.manifest)
        manifest.append(compressionElem)

        xml.write(self.manifest)

    @staticmethod
    def availableCompressionFormat(printIt=False):
        list = ('gz', 'bz2')

        if printIt:
            print 'Available compression format: %s' % ', '.join(list)
            sys.exit(0)
        else:
            return list
