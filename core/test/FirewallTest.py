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
import unittest
import re
import os
import sys
import commands

import stratuslab.system.BaseSystem as system
from stratuslab.system.BaseSystem import BaseSystem as Firewall
from stratuslab.system.BaseSystem import enableIpForwarding
import tempfile
import shutil

class FirewallTest(unittest.TestCase):

    def setUp(self):
        self.firewall = Firewall()
        self.firewall.verboseLevel = 0

    def tearDown(self):
        self.firewall = None

    def testFromRuleSpecToRuleAndTable(self):
        ruleSpec = {'rule':'foo'}
        rule, table = self.firewall._getRuleAndTableFromRuleSpec(ruleSpec)
        self.assertEquals(rule, 'foo')
        self.assertEquals(table, 'filter')

        ruleSpec = {'rule':'foo', 'table':'bar'}
        rule, table = self.firewall._getRuleAndTableFromRuleSpec(ruleSpec)
        self.assertEquals(rule, 'foo')
        self.assertEquals(table, 'bar')

    def testSetDeleteFirewallRule(self):
        ruleSpec = {'rule':'-A INPUT -p udp -m udp --dport 65534 -j ACCEPT'}

        self.firewall._setFirewallRule(ruleSpec)
        self.assertTrue(self._isIptablesRuleSet(ruleSpec['rule'], 'filter'))

        self.firewall._deleteFirewallRule(ruleSpec)
        self.assertTrue(not self._isIptablesRuleSet(ruleSpec['rule'], 'filter'))

    def _isIptablesRuleSet(self, rule, table):
        rules = commands.getoutput('iptables-save -t %s' % table)
        if re.search(rule, rules, re.M):
            return True
        return False
    
    def testConfigureIpForwarding(self):
        fileEnable_saved = system.FILE_IPFORWARD_HOT_ENABLE
        filePersist_saved = system.FILE_IPFORWARD_PERSIST

        system.FILE_IPFORWARD_HOT_ENABLE = tempfile.mkstemp()[1]
        open(system.FILE_IPFORWARD_HOT_ENABLE, 'w').write("1")
        
        system.FILE_IPFORWARD_PERSIST = tempfile.mkstemp()[1]

        fileEnable = system.FILE_IPFORWARD_HOT_ENABLE
        filePersist = system.FILE_IPFORWARD_PERSIST
        
        savedState = _fileRead(fileEnable) 
        savedConfig = _fileRead(filePersist)
        
        enableIpForwarding()
        
        self.assertTrue(self._isIpForwardingEnabled(fileEnable))
        self.assertTrue(self._isIpForwardingPersistedAndOn(filePersist))

        system.FILE_IPFORWARD_HOT_ENABLE = fileEnable_saved
        system.FILE_IPFORWARD_PERSIST = filePersist_saved

        fileEnable = system.FILE_IPFORWARD_HOT_ENABLE
        filePersist = system.FILE_IPFORWARD_PERSIST
        
    def _isIpForwardingEnabled(self, filename):
        return _fileRead(filename).strip() == '1'
        
    def _isIpForwardingPersistedAndOn(self, filename):
        config = _fileRead(filename).split('\n')
        for line in config:
            if line.startswith('net.ipv4.ip_forward'):
                return line.split('=')[1].strip() == '1'
        return False
            
def _fileRead(fn):
    return file(fn).read()
def _fileWrite(fn, data):
    file(fn, 'w').write(data)

if __name__ == "__main__":
    unittest.main()
