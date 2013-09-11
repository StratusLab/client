#!/usr/bin/env python
#
# Copyright (c) 2013, Centre National de la Recherche Scientifique (CNRS)
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
import stat

class TMMakeSwap(object):
    ''' 
    Creates a swap file with the size given in KB.
    '''

    # Debug option
    PRINT_TRACE_ON_ERROR = True
    DEFAULT_VERBOSELEVEL = 0

    # Swap disk permissions = 0660
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
        
        TMMakeSwap._checkArgs(self.args)

        fname = self.args[1]
        bytes = TMMakeSwap._parseBytes(self.args[2])

        TMMakeSwap._makeEmptyFile(fname, kb)

    def _cleanup(self):
        pass

    @staticmethod
    def _checkArgs(args):
        if (not args or len(args) < 3):
            raise ValueError('must have at least two arguments: swap filename and size (in KB)')

    @staticmethod
    def _parseBytes(kb):
        """
        Parse the given size (a string in KB) into the number of bytes
        in the file.  This will raise a ValueError if the string
        cannot be parsed as an integer.
        """
        return (int(kb) * 1000)

    @staticmethod
    def _makeEmptyFile(fname, bytes):
        """
        Creates a sparse file with zeros on operating systems that
        support it.  For other systems, it will create a regular file
        of the given size.  The contents may or may not be zeroed.
        """
        with open(fname, 'wb') as f:
            f.seek(bytes - 1) 
            f.write('\0') 
        return fname

