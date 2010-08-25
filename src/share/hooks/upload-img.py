#!/usr/bin/env python

import os
import os.path
import pickle
import subprocess
import sys
from optparse import OptionParser

class UploadImage(object):
    def __init__(self):
        self.parser = OptionParser()
        self.optionsDesc = {
            'vmAddress': 'address of the machine',
            'diskPath': 'path to the disk to save',
            'sshKey': 'location of the key to use to connect to the machine',
            'manifestPath': 'location of the manifest on the machine',
            'uploadInfoPickled': 'pickled upload informations',
        }

        self.parseOptions()
        self.checkOptions()
        self.unpickleUploadInfo()
        self.retrieveManifest()
        self.uploadImage()

    def parseOptions(self):
        self.parser.usage = '''%prog [options]'''
        self.parser.add_option('--address', dest='vmAddress', metavar='ADDRESS',
                help=self.optionsDesc['vmAddress'])
        self.parser.add_option('--disk', dest='diskPath', metavar='FILENAME',
                help=self.optionsDesc['diskPath'])
        self.parser.add_option('--ssh-key', dest='sshKey', metavar='FILENAME',
                help=self.optionsDesc['sshKey'])
        self.parser.add_option('--manifest', dest='manifestPath', metavar='FILENAME',
                help=self.optionsDesc['manifestPath'])
        self.parser.add_option('--upload-info', dest='uploadInfoPickled', metavar='PICKLE',
                help=self.optionsDesc['uploadInfoPickled'])
        self.parser.add_option('--hook', dest='hookCall', action='store_true',
                help='exit silently when arguement error (for hook call)',
                default=False)

        self.options, _ = self.parser.parse_args()

    def checkOptions(self):
        for attr, desc in self.optionsDesc.items():
            if not getattr(self.options, attr):
                self.error('Unspecified %s' % desc)

        if not os.path.isfile(self.options.diskPath):
            self.error('Disk does not exist')
        if not os.path.isfile(self.options.sshKey):
            self.error('SSH key does not exist')

    def unpickleUploadInfo(self):
        self.uploadInfo = pickle.loads()

    def retrieveManifest(self):
        ret = self.scp('root@%s:%s' % (self.options.vmAddress, self.options.manifestPath),
                  '%s.manifest.xml' % self.options.diskPath )

        if ret != 0:
            raise Exception('An error occured while retrieving manifest')

    def uploadImage(self):
        if os.getenv('STRATUSLAB_LOCATION'):
            scriptLocation = '%s/scripts'
        else:
            scriptLocation = '/usr/bin'

        uploadCmd = ['%s/stratus-upload-image' % scriptLocation,
                     '--repository', self.uploadInfo['repoAddress'],
                     '--curl-option', self.uploadInfo['uploadOption'],
                     '--compress', self.uploadInfo['compressionFormat'],
                     '--repo-username', self.uploadInfo['repoUsername'],
                     '--repo-password', self.uploadInfo['repoPassword'],
                     '%s.manifest' % self.options.diskPath,
                    ]

        if self.uploadInfo['forceUpload']:
            uploadCmd.append('--force')

    
    def sshCmd(self, cmd, timeout=5, **kwargs):
        sshCmd = ['ssh', '-p', '22', '-o', 'ConnectTimeout=%s' % timeout,
                  '-o', 'StrictHostKeyChecking=no', '-i', self.options.sshKey,
                  'root@%s' % self.options.vmAddress, cmd]

        return self.execute(sshCmd, **kwargs)

    def scp(self, src, dest, **kwargs):
        scpCmd = ['scp', '-i', self.options.sshKey, src, dest]

        return self.execute(*scpCmd, **kwargs)

    def execute(self, cmd, **kwargs):
        wait = not kwargs.get('noWait', False)

        if kwargs.has_key('noWait'):
            del kwargs['noWait']

        process = subprocess.Popen(cmd, **kwargs)

        if wait:
            process.wait()
            return process.returncode

        return process

    def error(self, message):
        if self.options.hookCall:
            sys.exit(0)
        else:
            self.parser.error(message)

if __name__ == '__main__':
    try:
        UploadImage()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'