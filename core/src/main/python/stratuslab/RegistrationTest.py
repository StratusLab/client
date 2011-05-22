#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Centre National de la Recherche Scientifique (CNRS)
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

import ldap
import ldap.modlist as modlist

class RegistrationTest(unittest.TestCase):

    baseUrl = 'https://localhost:8444/'
    ldapUrl = 'ldap://localhost:10389/'

    managerDn = 'uid=admin,ou=system'
    managerPassword = 'secret'

    userDn = 'jsmith'
    userPassword = 'dummy_password'
    userPasswordNew = 'dummy_password1'
    
    baseDn = { 'users', 'ou=users,o=cloud', 
               'groups', 'ou=groups,o=cloud',
               'actions', 'ou=actions,o=cloud' } 

    def testManagerCanSearch(self):

        ldapObj = ldap.initialize(ldapUrl)
        ldapObj.simple_bind_s(managerDn, managerPassword)
        
        searchScope = ldap.SCOPE_SUBTREE
        searchFilter = 'objectClass=*'
        retrieveAttributes = None

        ldapResultId = ldapObj.search(baseDn['users'], searchScope, 
                                      searchFilter, retrieveAttributes)

        resultSet = []
        
        while 1:
            resultType, resultData = ldapObj.result(ldapResultId, 0)
            if (resultData != []):
                if resultType == ldap.RES_SEARCH_ENTRY:
                    resultSet.append(resultData)
            else:
                break
                    
        self.assertEqual(1, len(resultSet))


if __name__ == "__main__":
    unittest.main()

