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

class RegistrationTest(unittest.TestCase):

    baseUrl = 'https://localhost:8444'
    ldapUrl = 'ldaps://localhost:636/'

    managerDn = 'cn=admin,o=cloud'
    managerPassword = 'secret'

    username = 'jsmith'
    userDn = 'uid=jsmith,ou=users,o=cloud'
    userPassword = 'dummy_password'
    userPasswordNew = 'dummy_password1'
    
    baseDns = { 'users':'ou=users,o=cloud', 
                'groups':'ou=groups,o=cloud',
                'actions':'ou=actions,o=cloud' } 

    headers = {'cache-control':'no-cache'}

    def getLdapResultSet(self, ldapObj, ldapResultId):
        resultSet = []
        
        while 1:
            resultType, resultData = ldapObj.result(ldapResultId, 0)
            if (resultData != []):
                if resultType == ldap.RES_SEARCH_ENTRY:
                    resultSet.append(resultData)
            else:
                break
        
        return resultSet


    def pageExistsWithNonZeroLength(self, url):
        h = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
        resp, content = h.request(url);

        self.assertEqual(200, resp.status, url + ': invalid status ' + str(resp.status))

        length = len(content)
        self.assertTrue(length > 0, url + ': invalid length ' + str(length))


    def registerUseCase(self):
        h = httplib2.Http(disable_ssl_certificate_validation=True)
        h.follow_redirects = False

        data = {
            'uid':self.username, 
            'mail':'smith@example.org',
            'givenName':'john',
            'sn':'smith',
            'seeAlso':'cn=John Smith,o=StratusLab',
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

        # Ensure user is found in LDAP
        self.findUserInLdap()


    def findUserInLdap(self):

        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        searchScope = ldap.SCOPE_BASE
        searchFilter = 'objectClass=inetOrgPerson'
        retrieveAttributes = None

        ldapResultId = ldapObj.search(self.userDn, searchScope, 
                                      searchFilter, retrieveAttributes)
        
        resultSet = self.getLdapResultSet(ldapObj, ldapResultId)
        
        self.assertEqual(1, len(resultSet), 'user not found in LDAP: ' + self.userDn)


    def checkUserLdapPermissions(self):

        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.userDn, self.userPassword)
        
        searchScope = ldap.SCOPE_BASE
        searchFilter = 'objectClass=*'
        retrieveAttributes = None

        for key in self.baseDns.keys():
            baseDn = self.baseDns[key]
            ldapResultId = ldapObj.search(baseDn, searchScope, 
                                          searchFilter, retrieveAttributes)

            resultSet = self.getLdapResultSet(ldapObj, ldapResultId)
                    
            self.assertEqual(1, len(resultSet), 'user cannot read base object: ' + baseDn)


    def profileExistsWithNonZeroLength(self):
        h = httplib2.Http(".cache", disable_ssl_certificate_validation=True)
        h.add_credentials(self.username, self.userPassword)
        resp, content = h.request(self.baseUrl + '/profile/')

        self.assertEqual(200, resp.status, url + ': invalid status ' + str(resp.status))

        length = len(content)
        self.assertTrue(length > 0, url + ': invalid length ' + str(length))


    def startPasswordReset(self):
        h = httplib2.Http(disable_ssl_certificate_validation=True)
        h.follow_redirects = False

        data = {
            'uid':self.username
            }

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        body = urllib.urlencode(data)
        
        url = self.baseUrl + '/reset/'
        resp, content = h.request(url, "POST", body=body, headers=headers)

        # A correct registration should return a redirect. 
        self.assertEqual(303, resp.status, url + ': invalid status ' + str(resp.status))


    def getActionsFromLdap(self):

        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        searchScope = ldap.SCOPE_SUBTREE
        searchFilter = 'objectClass=javaSerializedObject'
        retrieveAttributes = ['cn']

        baseDn = self.baseDns['actions']
        ldapResultId = ldapObj.search(baseDn, searchScope, 
                                      searchFilter, retrieveAttributes)
        
        resultSet = self.getLdapResultSet(ldapObj, ldapResultId)

        actionCnSet = set()
        for item in resultSet:
            actionCnSet.add(item[0][1]['cn'][0])

        return actionCnSet


    def confirmPasswordReset(self, actionUuid):
        h = httplib2.Http(disable_ssl_certificate_validation=True)

        url = self.baseUrl + '/action/' + actionUuid
        resp, content = h.request(url)

        self.assertEqual(200, resp.status, url + ': invalid status ' + str(resp.status))


    def resetPasswordUseCase(self):

            # Try to reset the user password.
            previousActions = self.getActionsFromLdap()
            self.startPasswordReset()
            currentActions = self.getActionsFromLdap()
            newActions = currentActions.difference(previousActions)
            self.assertEqual(1, len(newActions))
            actionUuid = newActions.pop()
            self.confirmPasswordReset(actionUuid)

            # Accessing service with old password should fail.
            try:
                self.checkUserLdapPermissions()
            except ldap.INVALID_CREDENTIALS:
                # Ok, tried to connect with wrong password.
                consumed = True


    def deleteUserFromLdap(self):
        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        ldapObj.delete_s(self.userDn)


    def testRegistrationServicePagesExist(self):
        urls = [ '/', '/register/', '/policies/', '/reset/' ]
        for url in urls:
            self.pageExistsWithNonZeroLength(self.baseUrl + url);
        

    def testLdapBaseObjectsExist(self):

        ldapObj = ldap.initialize(self.ldapUrl)
        ldapObj.simple_bind_s(self.managerDn, self.managerPassword)
        
        searchScope = ldap.SCOPE_BASE
        searchFilter = 'objectClass=*'
        retrieveAttributes = None

        for key in self.baseDns.keys():
            baseDn = self.baseDns[key]
            ldapResultId = ldapObj.search(baseDn, searchScope, 
                                          searchFilter, retrieveAttributes)

            resultSet = self.getLdapResultSet(ldapObj, ldapResultId)
                    
            self.assertEqual(1, len(resultSet), 'problem with base object: ' + baseDn)


    def testRegisterUser(self):
        try:

            self.registerUseCase()

            self.checkUserLdapPermissions()

            self.resetPasswordUseCase()

        finally:                
            self.deleteUserFromLdap()

if __name__ == "__main__":
    unittest.main()

