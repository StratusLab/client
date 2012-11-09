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

import Util
import hashlib
import gzip
import bz2
from Exceptions import ExecutionException

class Compressor(object):

    compressionFormats = ('gz', 'bz2')

    @staticmethod
    def compress(filename):
        pass
        
    @staticmethod        
    def inflate(filename):
        cmd = Compressor._getInflateCommand(filename)
    
        ret = Util.execute([cmd, filename])
        if ret != 0:
            raise ExecutionException('Error inflating file: %s' % filename)

    @staticmethod
    def getCompressionFormat(filename):
        """If the file suffix (ignoring case) is in the list of supported
           compression formats, this returns the compression format.
           Otherwise, it returns the empty string. """
        suffix = Util.fileGetExtension(filename).lower()
        if suffix in Compressor.compressionFormats:
            return suffix
        else:
            return ''

    @staticmethod
    def openCompressedFile(filename, options='rb'):
        """Returns an open file handle for the given filename.  If the
           filename ends with a gzip or bzip2 suffix, then the file is
           opened as a gzip or bzip2 file.  Otherwise it is opened
           without any compression filter."""
        type = Compressor.getCompressionFormat(filename)
        if (type == 'gz'):
            return gzip.open(filename, options)
        elif (type == 'bz2'):
            return bz2.BZ2File(filename, options)
        else:
            return open(filename, options)

    @staticmethod
    def checksum_file(filename, checksums=[], chunk_size=1024*1024*10):
        """Return dictionary of checksums."""

        return Compressor._checksum_f(Compressor.openCompressedFile(filename, 'rb'), checksums, chunk_size)

    @staticmethod
    def _checksum_f(f, checksums=[], chunk_size=1024*1024*10):
        """Returns a tuple with the file size in bytes and a dictionary of
        checksums. The file named by the file handle will be fully read
        if checksums are requested.  This method will close the file
        handle."""
        
        #
        # "with" cannot be used here because the gzip library in python
        # 2.6 doesn't support the __exit__ attribute needed for it
        #
        try: 

            if not checksums:
                return {}

            digesters = []
            try:
                digesters = map(hashlib.new, checksums)
            except ValueError as e:
                raise ExecutionException('%s' % e)

            bytes = 0
            for chunk in iter((lambda:f.read(chunk_size)),''):
                bytes += len(chunk)
                for digester in digesters:
                    digester.update(chunk)

            digests = [d.hexdigest() for d in digesters]

            return (bytes, dict(zip(checksums, digests)))

        finally:
            f.close()

    @staticmethod        
    def _getCompressionCommand(filename):
        format = filename.split('.')[-1]
        return Compressor._getCompressionCommandByFormat(format)

    @staticmethod
    def _getCompressionCommandByFormat(format):
        if format == 'gz':
            cmd = 'gzip'
        elif format == 'bz2':
            cmd = 'bzip2'
        else:
            raise NotImplementedError('Unknown compression format: %s' % format)

        return cmd

    @staticmethod        
    def _getInflateCommand(filename):
        format = filename.split('.')[-1]

        if format == 'gz':
            cmd = 'gunzip'
        elif format == 'bz2':
            cmd = 'bunzip2'
        else:
            raise NotImplementedError('Unknown compression format: %s' % format)

        return cmd
