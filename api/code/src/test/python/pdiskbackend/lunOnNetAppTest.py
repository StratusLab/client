import unittest
from mock.mock import Mock

from stratuslab.pdiskbackend.backends.NetAppBackend import NetApp7Mode,\
    NetAppCluster

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

    def test_action_getturl(self):
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

if __name__ == "__main__":
    unittest.main()
