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

import ldap

from subprocess import call

class LdapAuthenticationTest(unittest.TestCase):

    oneEndpoint = 'onehost-5.lal.in2p3.fr'
    pemCert = '/tmp/stratuslab-test-user/stratuslab-test-user-cert.pem'
    pemKey = '/tmp/stratuslab-test-user/stratuslab-test-user-key.pem'
    baseUrl = 'https://onehost-5.lal.in2p3.fr:8444'
    ldapUrl = 'ldap://onehost-5.lal.in2p3.fr:389/'

    managerDn = 'cn=admin,o=cloud'
    managerPassword = 'secret'

    username = 'jsmith'
    userDn = 'uid=jsmith,ou=users,o=cloud'
    userCertDn = 'CN=John Smith,OU=Test,O=StratusLab,C=EU'
    userPassword = 'dummy_password'

    cloudAccessDn = 'cn=cloud-access,ou=groups,o=cloud'
    
    headers = {'cache-control':'no-cache'}

    def registerUser(self):
        h = httplib2.Http(disable_ssl_certificate_validation=True)
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
        self.assertEqual(303, resp.status, url + ': invalid status ' + str(resp.status))


    def verifyProfile(self):
        h = httplib2.Http(disable_ssl_certificate_validation=True)
        h.add_credentials(self.username, self.userPassword)
        url = self.baseUrl + '/profile/'
        resp, content = h.request(url)

        self.assertEqual(200, resp.status, url + ': invalid status ' + str(resp.status))

        length = len(content)
        self.assertTrue(length > 0, url + ': invalid length ' + str(length))


    def getCloudAccessGroup(self):
        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        searchScope = ldap.SCOPE_BASE
        searchFilter = '(&(objectClass=groupOfUniqueNames)(cn=cloud-access))'
        retrieveAttributes = [ 'uniqueMember' ]

        resultData = ldapObj.search_s(self.cloudAccessDn, searchScope, 
                                      searchFilter, retrieveAttributes)

        self.assertTrue(len(resultData) > 0, "no cloud-access group found encountered")
        self.assertTrue(len(resultData[0]) > 0, "malformed tuple for group information")

        return resultData[0][1]


    def authorizeUser(self):
        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)

        modlist = [(ldap.MOD_ADD, 'uniquemember', self.userDn)]

        ldapObj.modify_s(self.cloudAccessDn, modlist)


    def unauthorizeUser(self):
        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)

        modlist = [(ldap.MOD_DELETE, 'uniquemember', self.userDn)]

        ldapObj.modify_s(self.cloudAccessDn, modlist)


    def deleteUserFromLdap(self):
        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        ldapObj.delete_s(self.userDn)


    def tryUsernamePassword(self):
        cmd = [ 'stratus-describe-instance', 
                '--endpoint', self.oneEndpoint, 
                '-u', self.username, 
                '-p', self.userPassword ]

        return call(cmd)


    def tryCertificate(self):
        cmd = [ 'stratus-describe-instance', 
                '--endpoint', self.oneEndpoint, 
                '--pem-cert', self.pemCert, 
                '--pem-key', self.pemKey ]

        return call(cmd)


    def testLdapAuthentication(self):

        try:
            
            rc = self.tryUsernamePassword()
            self.assertTrue(rc != 0, 'unregistered user accessed service with username password')

            rc = self.tryCertificate()
            self.assertTrue(rc != 0, 'unregistered user accessed service with certificate')

            self.registerUser()
            self.verifyProfile()

            rc = self.tryUsernamePassword()
            self.assertTrue(rc != 0, 'user without role accessed service with username password')

            rc = self.tryCertificate()
            self.assertTrue(rc != 0, 'user without role accessed service with certificate')

            self.authorizeUser()

            rc = self.tryUsernamePassword()
            self.assertTrue(rc == 0, 'registered user with role could not access service with username password')
            
            rc = self.tryCertificate()
            self.assertTrue(rc == 0, 'registered user with role could not access service with certificate')
            
        finally:
            self.unauthorizeUser()
            self.deleteUserFromLdap()


if __name__ == "__main__":
    unittest.main()

