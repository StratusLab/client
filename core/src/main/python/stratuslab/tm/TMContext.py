#!/usr/bin/env python
#
# Copyright (c) 2012, Centre National de la Recherche Scientifique (CNRS)
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
import base64
import os
import re
import shutil
import stat

from os.path import dirname
from tempfile import mkstemp, mkdtemp

from stratuslab.Util import execute
from stratuslab.cloudinit.Util import decodeMultipartAsJson

class TMContext(object):
    ''' Create the disk with context information.  This is a CDROM for 
        standard OpenNebula/HEPiX contextualization.  It is a VFAT-formatted
        volume for cloud-init contextualization.
    '''

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSELEVEL = 0

    # Context disk permissions = 0660
    DISK_PERMS = (stat.S_IRUSR | stat.S_IWUSR |
                  stat.S_IRGRP | stat.S_IWGRP)

    def __init__(self, args, **kwargs):
        self.args = args

    def run(self):
        try:
            self._run()
        finally:
            self._cleanup()

    def _run(self):
        
        TMContext._checkArgs(self.args)

        contextFile = self.args[1]
        contextDiskFile = self.args[2]
        cdromFiles = self.args[1:]
        cdromFiles.remove(contextDiskFile)

        # hack to remove the node from the destination
        contextDiskFile = contextDiskFile.split(':')[1]

        kvpairs = TMContext._parseContextFile(contextFile)

        method = kvpairs.get('context_method', 'opennebula')
        if (method == 'cloud-init'):
            TMContext._doCloudInit(contextDiskFile, kvpairs)
        else:
            TMContext._doOpenNebula(contextDiskFile, cdromFiles)

    def _cleanup(self):
        pass

    @staticmethod
    def _checkArgs(args):
        if (not args or len(args) < 3):
            raise ValueError('must have at least two arguments: destination disk and context file')

    '''
       This does a "dirty" parsing of the context file looking only
       for the lines with the keys CONTEXT_METHOD,
       CLOUD_INIT_USER_DATA and CLOUD_INIT_AUTHORIZED_KEYS.  All of
       the other key-value pairs do not need to be understood by this
       class.  A map with these values (if found) are returned. 
    '''
    @staticmethod
    def _parseContextFile(context_file):
        result = {}
        with open(context_file, 'r') as f:
            for line in f:
                match = re.match('\s*CONTEXT_METHOD\s*=\s*"(.+)".*', line)
                if match:
                    result['context_method'] = match.group(1).strip()
                match = re.match('\s*CLOUD_INIT_USER_DATA\s*=\s*"(.+)".*', line)
                if match:
                    result['user_data'] = match.group(1).strip()
                match = re.match('\s*CLOUD_INIT_AUTHORIZED_KEYS\s*=\s*"(.+)".*', line)
                if match:
                    result['authorized_keys'] = match.group(1).strip()
        return result

    @staticmethod
    def _doOpenNebula(contextDiskFile, cdromFiles):
        tmpdir = None
        image = None
        try:
            tmpdir = mkdtemp()
            for f in cdromFiles:
                shutil.copy(f, tmpdir)

            _, image = mkstemp()

            cmd = ["mkisofs", "-o", image, "-J", "-R", tmpdir]
            rc = execute(cmd)
            if (rc != 0):
                raise Exception("error creating cdrom")

            os.chmod(image, TMContext.DISK_PERMS)

            print image
            print contextDiskFile
            print tmpdir
            os.makedirs(os.path.dirname(contextDiskFile))
            shutil.copy(image, contextDiskFile)

        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, True)
            if image:
                os.remove(image)


    @staticmethod
    def _doCloudInit(contextDiskFile, params):
        tmpdir = None
        image = None
        try:
            tmpdir = mkdtemp()

            image = os.path.join(tmpdir, "disk.vfat")
            mnt_point = os.path.join(tmpdir, "context")
            os.mkdir(mnt_point)

            print tmpdir
            print image
            print mnt_point

            cmd = ["mkfs.vfat", "-v", "-C", image, "1024"]
            print cmd
            rc = execute(cmd)
            print rc
            if (rc != 0):
                raise Exception('cannot create VFAT file system for cloud-init')

            cmd = ["mount", "-o", "loop", image, mnt_point]
            rc = execute(cmd)
            if (rc != 0):
                raise Exception('cannot mount VFAT file system for cloud-init')

            try:
                b64_content = params['authorized_keys']

                ssh_dir = os.path.join(mnt_point, 'root', '.ssh')
                os.makedirs(ssh_dir)

                keys_file = os.path.join(ssh_dir, 'authorized_keys')

                with open(keys_file, 'wb') as f:
                    content = base64.b64decode(b64_content)
                    f.write(content)

            except KeyError:
                pass

            try:
                encoded_content = params['user_data']
                meta_content = decodeMultipartAsJson('local', encoded_content)

                meta_file = os.path.join(mnt_point, 'meta.js')

                with open(meta_file, 'wb') as f:
                    f.write(meta_content)

            except KeyError:
                pass

            cmd = ["umount", mnt_point]
            rc = execute(cmd)
            if (rc != 0):
                raise Exception('cannot umount VFAT file system for cloud-init')

            os.chmod(image, TMContext.DISK_PERMS)

            shutil.copy(image, contextDiskFile)

        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, True)
