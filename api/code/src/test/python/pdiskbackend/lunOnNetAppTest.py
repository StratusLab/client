import unittest
from mock.mock import Mock

from stratuslab.pdiskbackend.backends.NetAppBackend import NetApp7Mode,\
    NetAppCluster

#from stratuslab.pdiskbackend.utils import initialize_logger
#initialize_logger('console', 3)

class lunOnNetAppTest(unittest.TestCase):

    def test_action_check(self):
        from stratuslab.pdiskbackend.LUN import LUN
        lun = LUN('123', proxy=NetApp7Mode('localhost', 'jay', '/foo/bar', 
                                           '/netapp/volume', 'namespace', 
                                           'initiatorGroup', 'snapshotPrefix'))

        lun._runCommand = Mock(return_value=(0, 'success'))
        assert (0, 'success') == lun._execute_action('check')

        lun._runCommand = Mock(return_value=(1, 'failure'))
        assert (1, 'failure') == lun._execute_action('check')

    def test_action_getturl_success(self):
        IQN = 'iqn.1992-08.com.netapp:sn.307fb4db630d11e38ca5123478563412:vs.19'
        LUN_ID = '123'
        PORTAL = 'localhost'

        def side_effect(action):
            if action == 'get_target':
                return (0, """vserver  target-name                                                      
-------- ---------------------------------------------------------------- 
hniscsi1 %s
    """ % IQN)
            elif action == 'get_lun':
                return (0, """ABC: abc
LUN ID: %s""" % LUN_ID)

        from stratuslab.pdiskbackend import CommandRunner
        CommandRunner.CommandRunner._getStatusOutputOrRetry = Mock(side_effect=side_effect)

        from stratuslab.pdiskbackend.LUN import LUN
        lun = LUN('123', proxy=NetAppCluster(PORTAL, 'jay', '/foo/bar', 
                                             '/netapp/volume', 'namespace', 
                                             'initiatorGroup', 'snapshotPrefix'))
        turl = 'iscsi://%s:3260/%s:%s' % (PORTAL, IQN, LUN_ID)
        assert (0, turl) == lun._execute_action('getturl')

    def test_action_getturl_failure(self):
        IQN = 'iqn.1992-08.com.netapp:sn.307fb4db630d11e38ca5123478563412:vs.19'
        PORTAL = 'localhost'

        def side_effect(action):
            if action == 'get_target':
                return (0, """vserver  target-name                                                      
-------- ---------------------------------------------------------------- 
hniscsi1 %s
    """ % IQN)
            elif action == 'get_lun':
                return (255, """There are no entries matching your query.""")

        from stratuslab.pdiskbackend import CommandRunner
        CommandRunner.CommandRunner._getStatusOutputOrRetry = Mock(side_effect=side_effect)

        from stratuslab.pdiskbackend.LUN import LUN
        lun = LUN('123', proxy=NetAppCluster(PORTAL, 'jay', '/foo/bar', 
                                             '/netapp/volume', 'namespace', 
                                             'initiatorGroup', 'snapshotPrefix'))
        status, _ = lun._execute_action('getturl')
        assert 255 == status

    def test_action_delete(self):
        from stratuslab.pdiskbackend import CommandRunner
        CommandRunner.CommandRunner._getStatusOutputOrRetry = Mock(return_value=(255, """
Error: There are no entries matching your query."""))

        from stratuslab.pdiskbackend.LUN import LUN
        lun = LUN('123', proxy=NetAppCluster('localhost', 'jay', '/foo/bar', 
                                             '/netapp/volume', 'namespace', 
                                             'initiatorGroup', 'snapshotPrefix'))
        assert (0, '') == lun._execute_action('delete')

    def test_action_snapshot_failure(self):
        PORTAL = 'localhost'

        def side_effect(action):
            if action == 'snapshot':
                return (255, """Error: command failed: The Snapshot(tm) copy name already exists""")
            elif action == 'clone':
                return (255, """Error: command failed: Clone start failed: Clone operation failed to start:
Clone file exists.""")

        from stratuslab.pdiskbackend import CommandRunner
        CommandRunner.CommandRunner._getStatusOutputOrRetry = Mock(side_effect=side_effect)

        from stratuslab.pdiskbackend.LUN import LUN
        lun = LUN('123', proxy=NetAppCluster(PORTAL, 'jay', '/foo/bar', 
                                             '/netapp/volume', 'namespace', 
                                             'initiatorGroup', 'snapshotPrefix'))
        lun.associatedLUN = Mock()
        lun.associatedLUN.getUuid = Mock(return_value='foo')
        assert (255, '') == lun._execute_action('snapshot')

if __name__ == "__main__":
    unittest.main()
