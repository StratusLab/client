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

import sys
sys.path.append('/var/lib/stratuslab/python')

import re
import shutil
import stat

from os.path import dirname, join
from tempfile import mkstemp, mkdtemp

from stratuslab.Util import execute, scp
from stratuslab.cloudinit.Util import decodeMultipartAsJson

class TMMakeVFAT(object):
    '''
    Create a VFAT volume with the provided contents.
    '''

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSELEVEL = 0

    # Context disk permissions = 0664
    DISK_PERMS = (stat.S_IRUSR | stat.S_IWUSR |
                  stat.S_IRGRP | stat.S_IWGRP |
                  stat.S_IROTH)

    def __init__(self, args, **kwargs):
        self.args = args

    def run(self):
        try:
            print self._run()
        finally:
            self._cleanup()

    def _run(self):
        
        TMMakeVFAT._checkArgs(self.args)

        src = self.args[1]
        vfat_fs = self.args[2]

        TMMakeVFAT._createDrive(src, vfat_fs)

    def _cleanup(self):
        pass

    @staticmethod
    def _checkArgs(args):
        if (not args or len(args) != 3):
            raise ValueError('provide source directory and VFAT image file')

    '''
    Only three files/directories can be used for the cloud-init
    configuration: etc, root, and meta.js.  Copy just these files from
    the source directory to the destination directory, presumably the
    VFAT image.
    '''
    @staticmethod
    def _copyCloudInitFiles(src, dst):
        etc_src = join(src, "etc")
        if os.path.exists(etc_src):
            etc_dst = join(dst, "etc")
            shutil.copytree(etc_src, etc_dst)
            
        root_src = join(src, "root")
        if os.path.exists(root_src):
            root_dst = join(dst, "root")
            shutil.copytree(root_src, root_dst)
                
        meta_js_src = join(src, "meta.js")
        if os.path.exists(meta_js_src): 
            meta_js_dst = join(dst, "meta.js")
            shutil.copyfile(meta_js_src, meta_js_dst)


    @staticmethod
    def _createDrive(src, image):
        tmpdir = None
        try:
            mnt_point = mkdtemp()

            cmd = ["mkfs.vfat", "-n", "_CLOUD_INIT", "-v", image]
            rc = execute(cmd)
            if (rc != 0):
                raise Exception('cannot format VFAT file system for cloud-init')

            cmd = ["mount", "-o", "loop", image, mnt_point]
            rc = execute(cmd)
            if (rc != 0):
                raise Exception('cannot mount VFAT file system for cloud-init')

            TMMakeVFAT._copyCloudInitFiles(src, mnt_point)

            cmd = ["umount", mnt_point]
            rc = execute(cmd)
            if (rc != 0):
                raise Exception('cannot umount VFAT file system for cloud-init')

            os.chmod(image, TMMakeVFAT.DISK_PERMS)

        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, True)

if __name__ == '__main__':
    try:
        tm = TMMakeVFAT(sys.argv)
        tm.run()
    except Exception, e:
        print >> sys.stderr, 'ERROR MESSAGE --8<------'
        print >> sys.stderr, '%s: %s' % (os.path.basename(__file__), e)
        print >> sys.stderr, 'ERROR MESSAGE ------>8--'
        if TMMakeVFAT.PRINT_TRACE_ON_ERROR:
            raise
        sys.exit(1)
