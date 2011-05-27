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
import httplib2
import urllib
import random
import string

import ldap
import ldap.modlist as modlist

class LdapAuthenticationTest(unittest.TestCase):

    baseUrl = 'https://localhost:8444'
    ldapUrl = 'ldap://localhost:10389/'

    managerDn = 'uid=admin,ou=system'
    managerPassword = 'secret'

    username = 'jsmith'
    userDn = 'uid=jsmith,ou=users,o=cloud'
    userCertDn = 'should be parameter'
    userPassword = 'dummy_password'

    cloudAccessDn = 'cn=cloud-access,ou=groups,o=cloud'
    
    headers = {'cache-control':'no-cache'}


    def registerUser(self):
        h = httplib2.Http()
        h.follow_redirects = False

        data = {
            'uid':self.username, 
            'mail':'smith@example.org',
            'givenName':'john',
            'sn':'smith',
            'seeAlso':self.userCertDn,
            'newUserPassword':self.userPassword,
            'newUserPasswordCheck':self.userPassword,
            'message':'I love clouds',
            'agreement':'true'
            }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = urllib.urlencode(data)
        
        url = self.baseUrl + '/users/'
        resp, content = h.request(url, "POST", body=body, headers=headers)

        # A correct registration should return a redirect. 
        self.assertEquals(303, resp.status, url + ': invalid status ' + str(resp.status))


    def verifyProfile(self):
        h = httplib2.Http()
        h.add_credentials(self.username, self.userPassword)
        resp, content = h.request(self.baseUrl + '/profile/')

        self.assertEquals(200, resp.status, url + ': invalid status ' + str(resp.status))

        length = len(content)
        self.assertTrue(length > 0, url + ': invalid length ' + str(length))


    def authorizeUser(self):
        print getCloudAccessGroup()
        print 'authorizeUser'


    def getCloudAccessGroup(self):

        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        searchScope = ldap.SCOPE_ONE
        searchFilter = 'objectClass=groupOfUniqueMembers'
        retrieveAttributes = 'uniqueMembers'

        return ldapObj.search_s(self.cloudAccessDn, searchScope, 
                                searchFilter, retrieveAttributes)


    def deleteUserFromLdap(self):
        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        ldapObj.delete_s(self.userDn)


    def testLdapAuthentication(self):

        try:

            self.registerUser()
            self.verifyProfile()
            self.authorizeUser()
        
        finally:

            self.deleteUserFromLdap()


if __name__ == "__main__":
    unittest.main()

