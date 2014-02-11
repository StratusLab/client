import os
import tempfile
import unittest
from mock.mock import Mock

# Should go before importing Backend 
from stratuslab.pdiskbackend.utils import EXITCODE_PDISK_OP_FAILED, Logger
Logger._add_file_logger = Mock()
Logger._add_syslog_logger = Mock()

from stratuslab.pdiskbackend.backends.Backend import Backend
from stratuslab.pdiskbackend.backends.BackendCommand import BackendCommand
from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder

class BackendTest(unittest.TestCase):

    def setUp(self):
        fd, self.cfg_fname = tempfile.mkstemp()
        os.close(fd)

    def tearDown(self):
        os.unlink(self.cfg_fname)

    def test_getCmd_missing_action(self):
        backend = Backend(ConfigHolder(self.cfg_fname))
        try:
            backend.getCmd('').next()
        except SystemExit as ex:
            assert ex.code == EXITCODE_PDISK_OP_FAILED
        else:
            self.fail('Should have raised SystemExit')

    def test_getCmd_default_actions(self):
        for action in Backend.lun_backend_cmd_mapping.keys():
            backend = Backend(ConfigHolder(self.cfg_fname))
            assert None == backend.getCmd(action).next()

    def test_getCmd(self):
        _lun_backend_cmd_mapping = Backend.lun_backend_cmd_mapping.copy()
        _backend_cmds = Backend.backend_cmds.copy()

        Backend.lun_backend_cmd_mapping.update({'check': ['foo']})
        Backend.backend_cmds = {'foo': ['bar']}
        Backend._type = 'baz'
        try:
            backend = Backend(ConfigHolder(self.cfg_fname))
            backendCmd = backend.getCmd('check').next()
    
            assert None != backendCmd
            assert isinstance(backendCmd, BackendCommand)
            
            assert ['bar'] == backendCmd.command
        finally:
            Backend.lun_backend_cmd_mapping = _lun_backend_cmd_mapping
            Backend.backend_cmds = _backend_cmds

if __name__ == "__main__":
    unittest.main()
