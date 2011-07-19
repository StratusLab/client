'''
Created on Jul 5, 2011

@author: vagos
'''
import paramiko, utils
import os, commands, logging, sys
from logging import handlers
from pysqlite2 import dbapi2 as sqlite

class NFSStore():
    def __init__(self):
        self.utils = utils.Utils()
        
        # Make sure the sqlite file exists. if not, create it and add the table we need
        con = sqlite.connect(self.utils.db_file)
        cur = con.cursor()
        try:
            self.volumes = cur.execute('select * from volumes',
                            ).fetchall()
            if len(self.volumes) > 0 :
                print """Already discovered database file."""
        except sqlite.DatabaseError:
            cur.execute('create table volumes (volume_id text, access text, user text, size text, attached text, shared text, instance text, device text, deleted text)')
            con.commit()
        cur.close()
        con.close()
        
        ## Install logger
        LOG_FILENAME = self.utils.store_dir+'/logs/nfsstore.log'
        self.my_logger = logging.getLogger('NFSStore')
        self.my_logger.setLevel(logging.DEBUG)
        
        loghandler = handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=2*1024*1024, backupCount=5)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
        loghandler.setFormatter(formatter)
        self.my_logger.addHandler(loghandler)
        
    def sanity_check(self, values):
        try:
            volumes = self.utils.list_volumes(values)
            
            for volume in volumes:
                if not volume['instance'] == 'None':
                    host = commands.getoutput("onevm list | awk '{if ($1 == "+values['instance']+") print $7; }'")
                    if host == "" :
                        self.utils.volume_db_detached(volume)
            return 
        except:
            self.my_logger.debug("Error in sanity check")
            return 
    
    def attach(self, values):
        try:
            volumes = self.utils.list_volumes(values)
            found = False
            for volume in volumes:
                if volume['volume_id'] == values['volume_id'] and volume['attached']=='True':
                    return "Volume is already attached to instance: one-"+volume['instance']
                if volume['volume_id'] == values['volume_id'] :
                    found = True
            
            if not found:
                return "Volume not found!"
            
            host = commands.getoutput("onevm list | awk '{if ($1 == "+values['instance']+") print $7; }'")
            if host==None or host=="":
                return "Could not find instance"
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.my_logger.debug("Sending attach command to host " + host) 
            ssh.connect(host, username='root')
            stdin, stdout, stderr = ssh.exec_command('virsh attach-disk one-'+values['instance']+ ' ' + self.utils.store_dir+'/' + values['volume_id'] + ' ' + values['device'])
            ssh.close()
            self.utils.volume_db_attached(values)
            return "Volume attached."
        except:
            return "Could not attach volume. Please notify the system administrator."
    
    def detach(self, values):
        try:
            volumes = self.utils.list_volumes(values)
            found = False
            values_db = {}
            for volume in volumes:
                if volume['volume_id'] == values['volume_id'] and volume['attached']=='False':
                    return "Volume is not attached to an instance"
                if volume['volume_id'] == values['volume_id'] :
                    found = True
                    values_db['instance'] = volume['instance']
                    values_db['device'] = volume['device']
            
            self.my_logger.debug(values_db)
            
            if not found:
                return "Volume not found!"
            
            host = commands.getoutput("onevm list | grep one-"+values_db['instance']+" | awk '{print $7}'")
            if host==None or host=="":
                return "Could not find instance"
            
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.my_logger.debug("Sending detach command to host " + host) 
            ssh.connect(host, username='root')
            stdin, stdout, stderr = ssh.exec_command('virsh detach-disk one-'+values_db['instance']+ ' ' + values_db['device'])
            ssh.close()
            self.utils.volume_db_detached(values)
            return "Volume detached."
        except:
            return "Could not detach volume. Please notify the system administrator."
    
    
    def create(self, values):
        try:
            newvolume={}
            newvolume['volume_id'] = "vol-" + str(self.utils.get_last_volume_id()+1)
            newvolume['access'] = values['access'] or 'private'
            newvolume['user'] = values['user']
            newvolume['size'] = values['size']
            newvolume['attached'] = 'False'
            newvolume['shared'] = 'False'
            newvolume['instance'] = 'None'
            newvolume['device'] = 'None'
            newvolume['deleted'] = 'False'

            stdoutput = commands.getoutput("qemu-img create -f raw " + self.utils.store_dir + "/" + newvolume['volume_id'] + " " +  values['size'])
            self.utils.add_to_volume_db(newvolume)
            
            self.my_logger.debug("Creating image:" + stdoutput)
            
        except:
            return "Could not create volume. Please notify the system administrator."
        return "Volume "+ newvolume['volume_id'] +" created."
    
    def destroy(self, values):
        thevolume = {}
        try:
            self.my_logger.debug("Removing volume:" + values['volume_id'])
            thevolume = self.utils.get_volume_from_volume_db(values['volume_id'])
            
            if thevolume == None:
                return "This volume does not exist."
            
            if thevolume['attached'] == 'True':
                return "This volume is still attached on "+ thevolume['instance'] +"."
            
            if values['user'] == thevolume['user'] :
                stdoutput = commands.getoutput("rm -fr " + self.utils.store_dir + "/" + thevolume['volume_id'] + " " +  thevolume['size'])
                self.utils.rem_from_volume_db(thevolume) 
                self.my_logger.debug("Removed volume:" + stdoutput)
            else:
                return "This volume does not belong to you..."
        except:
            return "Could not destroy volume. Please notify the system administrator."
        return "Volume "+ values['volume_id'] +" destroyed."
    
    def share(self, values):
        pass
    
    def list(self, values):
        try:
            ## Added sanity check for closed instances
            self.sanity_check(values)
            
            volumes = self.utils.list_volumes(values)
            return_str="| Volume ID | Access | Owner  | Attached | Shared | Instance | Device |\n"
            return_str+="----------------------------------------------------------------------\n"
            
            for volume in volumes:
                if volume['deleted'] == 'False':
                    return_str += "| " + volume['volume_id'] + " | " + volume['access'] + " | " + volume['user'] + " | " + volume['attached'] + " | "+ volume['shared'] + " | " +volume['instance'] + " | "+ volume['device'] + " |\n"
            return return_str
        except:
            return "Could not list volumes. Please notify the system administrator."

    def show(self, values):
        pass
    