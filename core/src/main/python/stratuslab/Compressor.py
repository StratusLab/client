import os

import Util
from Exceptions import ExecutionException

class Compressor(object):

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
    def _getCompressionCommand(filename):
        format = filename.split('.')[-1]

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
