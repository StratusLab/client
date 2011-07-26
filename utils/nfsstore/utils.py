'''
Created on Jul 6, 2011

@author: vagos
'''

from pysqlite2 import dbapi2 as sqlite
import sys, os, logging, commands
from logging import handlers
from ConfigParser import ConfigParser

class Utils(object):
    '''
    This class holds utility functions. 
    '''
    
    def __init__(self):
        self.read_properties(os.getenv("HOME", "/etc") + "/volume.properties")
        stdoutput = commands.getoutput("mkdir -p "+self.store_dir+"/logs")
#        stdoutput = commands.getoutput("touch "+self.store_dir+"/logs/nfsstore.log")
        ## Install logger
        LOG_FILENAME = self.store_dir+'/logs/nfsstore.log'
        self.my_logger = logging.getLogger('Utils')
        self.my_logger.setLevel(logging.DEBUG)
        
        loghandler = handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        loghandler.setFormatter(formatter)
        self.my_logger.addHandler(loghandler)
        
    def read_properties(self, property_file="volume.properties"):
        """ process properties file """
        ## Reads the configuration properties
        cfg = ConfigParser()
        cfg.read(property_file)
        self.store_dir = cfg.get("config", "store_dir")
        self.db_file = cfg.get("config", "db_file")
        self.ip = cfg.get("config", "ip")
        self.port = cfg.get("config", "port")
            
    def get_last_volume_id(self):
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
        try:
            maxrowid = cur.execute(""" select max(rowid) from volumes """
                        ).fetchall()
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in select")
        if len(maxrowid) < 1:
            return 0
        elif maxrowid[0][0] == None:
            return 0
        else:
            return int(maxrowid[0][0])
        
    def list_volumes(self, volume):
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
        try:
            volumes = cur.execute(" select * from volumes where access=\"public\" or user=\"" +volume['user'] + "\""
                        ).fetchall()
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in select")
        if len(volumes) < 1:
            return "Could not list volumes"
        else:
            db_volumes=[]
            for db_volume in volumes:
                newvolume={}
                newvolume['volume_id'] = db_volume[0]
                newvolume['access'] = db_volume[1]
                newvolume['user'] = db_volume[2]
                newvolume['size'] = db_volume[3]
                newvolume['attached'] = db_volume[4]
                newvolume['shared'] = db_volume[5]
                newvolume['instance'] = db_volume[6]
                newvolume['device'] = db_volume[7]
                newvolume['deleted'] = db_volume[8]
                db_volumes.append(newvolume)
            return db_volumes 
        

    def volume_db_attached(self, volume):
        ## Update instance DB with provided instances (keeps previous entries!)
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
            
        try:
            cur.execute(" update volumes set attached=\"True\",instance=\""+volume['instance']+"\",device=\""+volume['device']+"\" where volume_id=\"" +volume['volume_id']+"\""
                        )
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in attach" )
            
        cur.close()
        con.close()
        
    def volume_db_detached(self, volume):
        ## Update instance DB with provided instances (keeps previous entries!)
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
            
        try:
            cur.execute(" update volumes set attached=\"False\",instance=\"None\",device=\"None\" where volume_id=\"" +volume['volume_id']+"\""
                        )
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in detach" )
            
        cur.close()
        con.close()
        
    def add_to_volume_db(self, volume):
        ## Update instance DB with provided instances (keeps previous entries!)
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
            
        try:
            cur.execute(""" insert into volumes(volume_id, access, user, size, attached, shared, instance, device, deleted) 
                                                values  (?,?,?,?,?,?,?,?,?)""",
                        (volume['volume_id'],volume['access'],volume['user'],volume['size'],volume['attached'], volume['shared'], volume['instance'], volume['device'], volume['deleted'] )
                        )
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in insert" )
            
        cur.close()
        con.close()
        
    def rem_from_volume_db(self, volume):
        ## Update instance DB with provided instances (keeps previous entries!)
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
            
        try:
            cur.execute('update volumes set deleted=\"True\" where volume_id=\"'+volume['volume_id']+"\""
                        )
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in update" )
            
        cur.close()
        con.close()
        
    def get_volume_from_volume_db(self, volume_id):
        ## Update instance DB with provided instances (keeps previous entries!)
        con = sqlite.connect(self.db_file)
        cur = con.cursor()
        
        volume_data = None
        try:
            volume_data = cur.execute('select * from volumes where volume_id=\"'+volume_id+'\"'
                        ).fetchall()
            con.commit()
        except sqlite.DatabaseError, e:
            self.my_logger.debug( e.message)
            self.my_logger.debug( "ERROR in select" )
        
        if len(volume_data)<1:
            self.my_logger.debug( "ERROR in select: not found" )
            return
        
        volume = {}
        volume['volume_id'] = volume_id
        volume['access'] = volume_data[0][1]
        volume['user'] = volume_data[0][2]
        volume['size'] = volume_data[0][3]
        volume['attached'] = volume_data[0][4]
        volume['instance'] = volume_data[0][5]
        volume['device'] = volume_data[0][6]
        
        cur.close()
        con.close()
        
        return volume