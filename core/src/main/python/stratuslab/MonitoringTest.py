#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, Telefonica I+D
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
import commands
import time

class MonitoringTest(unittest.TestCase):

    COLLECTD_CONFIG_FILE = '/opt/monitoring/conf/monitoring.properties'
    MYSQL_URL_DATA=['protocol', 'base','host', 'port', 'database']
    
    def _findAny(self, str, chars):
        best=-1
        for c in chars:
            pos=str.find(c)
            if best==-1 and pos>best:
                best=pos                
            elif pos<best and pos>=0:
                best=pos
        return best
    
    #
    # It parses a MySQL URL extracting host, port, protocol and database name. 
    def _parseDatabaseUrl(self):
        url=self._pd["mysqlurl"]
        chars='\/:'
        j=0
        
        tokPos=self._findAny(url, chars)
        while tokPos <> -1:
            if tokPos>0:
                value=url[:tokPos]                            
            else:               
               value=""
            tok=url[tokPos]               
            url=url[tokPos+1:]
            if tokPos>0:
                self._pd[MonitoringTest.MYSQL_URL_DATA[j]]=value
                j=j+1            
            tokPos=self._findAny(url, chars)            
        self._pd[MonitoringTest.MYSQL_URL_DATA[j]]=url        
        for a in self._dbData.keys():
            print "::::    %s -> %s" % (a, self._pd[a])
        
    # 
    # Reads the collectd monitoring.properties to get the database user and
    # password in order try connection with the database. 
    def _getProperties(self):
        try:
            #Pareamos el fichero de propiedades buscando las que nos interesan
            self._pd=dict() #pd={}
            pf=open(r"%s" % (MonitoringTest.COLLECTD_CONFIG_FILE), "rU")
            
            for propLine in pf:
                propLine=propLine.strip()
                if len(propLine)>0 and not propLine[0] in ('!','#',';'):
                    pos=propLine.find('=')
                    if (pos>0):
                        self._pd[propLine[:pos]]=propLine[pos+1:]                                    
            pf.close()           
            print "Usuario: %s / %s con url %s" % \
               (self._pd["mysqluser"], self._pd["mysqlpassword"], self._pd["mysqlurl"])
            self._parseDatabaseUrl()
        except:
            pass
      
    #
    # From a database query, we get the fields name in the first part and the 
    # data retrieved as query result in the second part of the returned tuple.
    def _getFieldAndValue(self, txt):
        n=txt.find("\n")
        print "%s \\\\ %s " % (txt[:n], txt[n+1:])       
        return (txt[:n], txt[n+1:])
    #
    # Every 30secs the collectd daemon writes on DB if it's working. So
    # we query the database, wait 30secs and query the database again. If
    # there are more entries, the daemon is working.
    def test01DatabaseDaemon(self):
        print "::::::::::"
        print "::: Testing database connetion"
        
        try:
           self._getProperties()
                
           cmd='mysql -u %s -p%s -h%s %s --batch -e "select count(1) as num from monitoringsample"' % \
            (self._pd["mysqluser"], self._pd["mysqlpassword"], 
                self._pd['host'], self._pd['database'])
        
           #first query.            
           (stat, txt)=commands.getstatusoutput(cmd)        
           print txt
           print ":::  mysqcmd=%d" % stat
           print "::::::::::::"        
           assert stat==0
           (field, value) = self._getFieldAndValue(txt)
        
           #wait time
           print "::::::: Sleeping 31 seconds before next query."
           time.sleep(31)
        
           # Second query...
           (stat, txt)=commands.getstatusoutput(cmd)                
           print txt
           print ":::  mysqcmd=%d" % stat
           print "::::::::::::"        
           assert stat==0
           (field, value2) = self._getFieldAndValue(txt)
           assert eval(value2)>eval(value)
        except Exception, e:
           print "::::::  This instalation might not work:" 
           print e.args[0]

if __name__ == "__main__":
    unittest.main()
