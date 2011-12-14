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

import stratuslab.Util as Util
import stratuslab.system.SystemFactory as SystemFactory
import hashlib
import time
import sys
from commands import getstatusoutput
import getpass

class MonitoringParsers(object):
    MYSQL_URL_DATA=['protocol', 'base','host', 'port', 'database']
    def __init__(self, url):
        self._pd=dict()
        self._url=url
        self.parseDatabaseUrl()
        
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
    def parseDatabaseUrl(self):
        url=self._url
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
                self._pd[MonitoringParsers.MYSQL_URL_DATA[j]]=value
                j=j+1            
            tokPos=self._findAny(url, chars)            
        self._pd[MonitoringParsers.MYSQL_URL_DATA[j]]=url        
        for a in self._pd.keys():
            print "::::    %s -> %s" % (a, self._pd[a])
    
    # 
    # Reads the collectd monitoring.properties to get the database user and
    # password in order try connection with the database. 
    def _getProperties(self):
        try:
            #Pareamos el fichero de propiedades buscando las que nos interesan
            pf=open(r"%s" % (Monitoring.COLLECTD_CONFIG_FILE), "rU")
            self._pd=dict() #pd={}
            for propLine in pf:
                propLine=propLine.strip()
                if len(propLine)>0 and not propLine[0] in ('!','#',';'):
                    pos=propLine.find('=')
                    if (pos>0):
                        self._pd[propLine[:pos]]=propLine[pos+1:]                                    
            pf.close()           
            print "Usuario: %s / %s con url %s" % \
               (self._pd["mysqluser"], self._pd["mysqlpassword"], self._pd["mysqlurl"])
            self.parseDatabaseUrl()
        except:
            pass
      
            
    def getPD(self):
        return self._pd
            
class Monitoring(object):
    COLLECTD_CONFIG_FILE = '/opt/monitoring/conf/monitoring.properties'
    def __init__(self, configHolder):     
        # this call makes all configuration parameters and command-line options
        # available as fields of self using the Camel case convention.
        # For example, the config parameter 'one_username' is available as self.oneUsername.
        configHolder.assign(self)
        self.system = SystemFactory.getSystem(self.frontendSystem, configHolder)
        
        # add your packages here 
        self.packages = ['collectd-base', 'collectd-basicprobes', 'collectd-java',
                         'collectd-api-rpm', 'collectd-collector-rpm', 'collectd-extendedprobes-rpm',
                         'mysql','mysql-server','mysql-libs','MySQL-python','']
       
        #pass the password to the sha1 constructor 
        self.createSha1 = hashlib.sha1(self.onePassword)
 
        #dump the password out in text 
        self.sha1Password = self.createSha1.hexdigest()
        #print "Password en sha1: "+self.sha1Password
        
        #monitoring probes properties        
        self.monitoringprops = {"mysqlurl":self.monitoringMysqlurl, \
                            "mysqluser":self.monitoringMysqluser, \
                            "mysqlpassword":self.monitoringMysqlpassword, \
                            "persistence.jars":self.monitoringPersistenceJars, \
                            "webserverport":self.monitoringWebserverport
                            }
        
    def _overrideValueInFile(self, key, value, fileName):
        # Here's how you could override config files...
        search = key + '='
        replace = key + '=' + value
        Util.appendOrReplaceInFile(fileName, search, replace)

    def _createTables(self):
        print " :: Tables creation"
        import MySQLdb
        
        conn=MySQLdb.connect(host = self._host,
               user = self._mysqluser,
               passwd = self._mysqlpassword,
               port = self._port,
               db = self._db)
        c=conn.cursor()
        ##------ TABLE nodedirectory ----
        c.execute("SET @saved_cs_client     = @@character_set_client")
        c.execute("SET character_set_client = utf8")
        c.execute("""CREATE TABLE IF NOT EXISTS `nodedirectory` (
                     `internalId` bigint(20) NOT NULL auto_increment,  
                     `fqn` varchar(255) default NULL,
                     `internalNodeId` bigint(20) NOT NULL,
                     `status` int(11) NOT NULL,
                     `fechaCreacion` datetime default NULL,
                     `fechaBorrado` datetime default NULL,
                     `tipo` int(11) NOT NULL,
                     `parent_internalId` bigint(20) default NULL,
                     PRIMARY KEY  (`internalId`),
                     KEY `FKCA54626B3CC47F10` (`parent_internalId`)
                  ) ENGINE=InnoDB AUTO_INCREMENT=105 DEFAULT CHARSET=latin1""")
        c.execute("SET character_set_client = @saved_cs_client")
        
        ##----- TABLE monitoringSAMPLE
        c.execute("SET character_set_client = utf8")
        c.execute("""CREATE TABLE IF NOT EXISTS `monitoringsample` (
             `id` bigint(20) NOT NULL auto_increment,
             `datetime` datetime default NULL,
             `day` int(11) NOT NULL,
             `month` int(11) NOT NULL,
             `year` int(11) NOT NULL,
             `hour` int(11) NOT NULL,
             `minute` int(11) NOT NULL,
             `value` varchar(255) default NULL,
             `measure_type` varchar(30) default NULL,
             `unit` varchar(30) default NULL,
             `associatedObject_internalId` bigint(20) default NULL,
             PRIMARY KEY  (`id`),
             KEY `FKD30AF432786DFD15` (`associatedObject_internalId`),
             INDEX `measure_type_index` (`measure_type`),
             CONSTRAINT `FKD30AF432786DFD15` FOREIGN KEY (`associatedObject_internalId`) 
             REFERENCES `nodedirectory` (`internalId`)
             ) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=latin1""")
        
        ###------- Table FQN
        c.execute("""create table  IF NOT EXISTS `fqn` ( 
             fqn varchar(255) not null, host varchar(64) not null, 
             plugin varchar(64) default null, primary key (fqn), 
             INDEX in1 (host,plugin)) ENGINE=InnoDB""")        
        conn.close()
        
        
    def _createDatabase(self):
        print " :: Database creation"
        import MySQLdb
       
        rootpass=self.monitoringMysqlRootPassword
        #rootpass=getpass.getpass("root password for mysql:")
        conn=MySQLdb.connect(host = self._host,
                user = "root",
                passwd = rootpass,
                port = self._port)
        createDatabase="create database if not exists %s" % self._db
        createUser = "create user '%s' identified by '%s'" % (self._mysqluser, self._mysqlpassword)
        createUserLocal = "create user '%s'@localhost identified by '%s'" % (self._mysqluser, self._mysqlpassword)
        grantAll="grant all on monitoring.* to '%s'" % self._mysqluser
        flushP="flush privileges"

        cursor=conn.cursor()
        cursor.execute(createDatabase)
        try:
           cursor.execute(createUser)
        except:
            pass
        try:
           cursor.execute(createUserLocal)
        except:
            pass
        cursor.execute(grantAll )
        cursor.execute(flushP)
        conn.close()
    
    def _testDatabaseConnection(self):
        print " :: Testing Database configuration"
        self._mysqluser=self.monitoringprops["mysqluser"]
        self._mysqlpassword=self.monitoringprops["mysqlpassword"]
        
        try:
           import MySQLdb
           conn=None
           try:
              conn=MySQLdb.connect(host = self._host,
                   port = self._port,
                   user = self._mysqluser,
                   passwd = self._mysqlpassword,
                   db = self._db)
              conn.close()                        
           except:               
               print ":::: Database creation needed"
               self._createDatabase()               
           self._createTables()
            
        except ImportError:            
            print "::::::  Error %d: %s" % (e.args[0], e.args[1])
        except MySQLdb.Error, e:
            print "::::::  Error %d: %s" % (e.args[0], e.args[1])
 
        
    #Check MySQL installation
    def _checkMysqlInstalled(self):
        print " :: Checking MySQL Installed"
        self._mysqlurl=self.monitoringprops["mysqlurl"]                        
        data=MonitoringParsers(self._mysqlurl)
        self._pd=data.getPD()
                
        #try:
        self._host=self._pd["host"]
        self._db=self._pd["database"]
        self._port=eval(self._pd["port"])
        
        if self._host in ["localhost", "127.0.0.1"]:
                cmd1="chkconfig mysqld on"                
                cmd2="service mysqld status"
                cmd3="service mysqld start"
                (stat, txt)=getstatusoutput(cmd1)
                (stat, txt)=getstatusoutput(cmd2)                
                #stat erroneo                                            
                if stat<>0:
                    (stat, txt)=getstatusoutput(cmd3)
        #except:
        #    pass
        
    def run(self):
        self._installPackages()
        self._configure()
        self._startServices()
        self._testDatabaseConnection()
        
    def _installPackages(self):
        if self.packages:
            print " :: Installing packages: "
            for p in self.packages:
                print " ::\t"+p
            print " ::"
            self.system.installPackages(self.packages)

    def _configure(self):
        # configure sm.properties file
        #print " :: Configuring "+self.smFile
        for k in self.monitoringprops:
            print k + " |-----> " + self.monitoringprops[k]
            self._overrideValueInFile(k, self.monitoringprops[k], self.monitoringProperties)
                
        print " ::"
    
    def _startServices(self):
        print " :: Starting collectd"
        self.system.execute(['/etc/init.d/collectd', 'restart'])
        self._checkMysqlInstalled()
        print " ::"
