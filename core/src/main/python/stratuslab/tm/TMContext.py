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
import os
import shutil
from os.path import dirname
from tempfile import mkstemp, mkdtemp

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
        self.contextDiskFile = None
        self.context = None
        self.srcFiles = None
        self.contextMethod = "opennebula"
        self.userData = None
        self.authorizedKeys = None

    def run(self):
        try:
            self._run()
        finally:
            self._cleanup()

    def _run(self):
        
        self._checkArgs()
        self._parseArgs()

        contextMethod = self.parseContextFile()
        if (self.contextMethod == 'opennebula'):
            self._makeCdrom()
        elif (self.contextMethod = 'cloud-init'):
            self._makeVfat()
        else:
            raise ValueError('context method must be "opennebula" or "cloud-init"')

    def _checkArgs(self):
        if len(self.args) < 2:
            raise ValueError('must have at least two arguments: destination disk and context file')

    def _parseArgs(self):
        self.contextDiskFile = self.args[0]
        self.context = self.args[1]
        self.srcFiles = self.args[1:]

    '''
       This does a "dirty" parsing of the context file looking only for the 
       lines with the keys CONTEXT_METHOD and CLOUD_INIT_USER_DATA.  All of
       the other key-value pairs do not need to be understood by this class.
    '''
    def _parseContextFile(self):
        f = None
        try:
            f = open(self.contextFile, 'r')
            for line in f:
                match = re.match('\s*CONTEXT_METHOD\s*=\s*([^\s]+).*', line)
                if match:
                    self.contextMethod = match.group(1)
                match = re.match('\s*CLOUD_INIT_USER_DATA\s*=\s*([^\s]+).*', line)
                if match:
                    self.userData = match.group(1)
                match = re.match('\s*CLOUD_INIT_AUTHORIZED_KEYS\s*=\s*([^\s]+).*', line)
                if match:
                    self.authorizedKeys = match.group(1)
        finally:
            if f:
                f.close()

    def _makeCdrom(self):
        tmpdir = None
        cdrom_image = None
        try:
            tmpdir = mkdtemp()
            for f in self.srcFiles:
                shutil.copy(f, tmpdir)

            cdrom_image = mkstemp()

            cmd = ["mkisofs", "-o", cdrom_image, "-J", "-R", tmpdir]
            execute(cmd)

            os.chmod(cdrom_image, DISK_PERMS)

            shutil.copy(cdrom_image, self.contextDiskFile)

        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, True)
            if cdrom_image:
                shutil.rm(cdrom_image)


    def _makeVfat(self):
        tmpdir = None
        image = None
        try:
            tmpdir = mkdtemp()

            image = os.join(tmpdir, "disk.vfat")
            mnt_point = os.join(tmpdir, "context")
            os.mkdir(mnt_point)

            cmd = ["mkfs.vfat", "-C", image, "1024"]
            execute(cmd)

            cmd = ["mount", "-o", "loop", mnt_point, image]
            execute(cmd)

            if self.authorizedKeys:
                os.write("x")

            if self.userData:
                os.write("x")

            cmd = ["umount", mnt_point]
            execute(cmd)

            os.chmod(image, DISK_PERMS)

            shutil.copy(image, self.contextDiskFile)

        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, True)
            if image:
                shutil.rm(image)


    def execute(cmd, returnType=None, exit=True, quiet=False, shell=False):
        printCmd(' '.join(cmd))
        if quiet:
            devNull = open(os.devnull, 'w')
            stdout = devNull
            stderr = devNull
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        p = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
        p.wait()

        if quiet:
            devNull.close()
        if returnType:
            return p.returncode
        else:

            out = p.stdout.read()
            err = p.stderr.read()
            if p.returncode == 0:
                if not quiet:
                    if out:
                        printAndFlush(out + '\n')
                    if err:
                        printAndFlush(err + '\n')
                return out
            else:
                printAndFlush('  [ERROR] Error executing command!\n')
                if out:
                    printAndFlush(out + '\n')
                if err:
                    printAndFlush(err + '\n')
                if exit:
                    raise Exception


    def printAndFlush(msg):
        sys.stdout.flush()
        print msg,
        sys.stdout.flush()

