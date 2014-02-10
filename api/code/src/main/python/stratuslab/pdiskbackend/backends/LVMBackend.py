
import re

from .Backend import Backend
from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder

def getBackendProxy(config):
    # Retrieve NetApp back-end mandatory attributes.
    # Mandatory attributes should be defined as keys of backend_attributes with an arbitrary value.
    # Key name must match the attribute name in the configuration file.
    backend_attributes = {'volume_name':''}
    proxy_name = config.get_proxy_name()
    config.set_backend_proxy_attributes(backend_attributes, proxy_name)    

    return LVMBackend(proxy_name,
                      backend_attributes['volume_name'],
                      backend_attributes['mgt_user_name'],
                      backend_attributes['mgt_user_private_key'],
                      configHolder=config) 

class LVMBackend(Backend):
    
    _type = 'lvm'
    
    # The following variables define which command to execute for each action.
    # They are documented in the superclass Backend.
    
    lun_backend_cmd_mapping = {'check':['check'],
                               'create':['create', 'add_device', 'reload_iscsi'],
                               'delete':['remove_device', 'reload_iscsi', 'wait2', 'dmremove', 'remove'],
                               'getturl' : ['getturl'],
                               # map is a required action for snapshot action but does nothing in LVM
                               'map':[],
                               'rebase':['rebase', 'add_device', 'reload_iscsi'],
                               'size':['size'],
                               'snapshot':['snapshot', 'add_device_snap', 'reload_iscsi_snap'],
                               'unmap':[],
                               }
    
    backend_cmds = {'add_device':[ '/bin/sed', '-i',
                                   '"1i<target iqn.2011-01.eu.stratuslab:%%UUID%%> \\n backing-store %%LOGVOL_PATH%% \\n </target>"',
                                   '/etc/stratuslab/iscsi.conf' ],
                    'add_device_snap':[ '/bin/sed', '-i',
                                        '"1i<target iqn.2011-01.eu.stratuslab:%%SNAP_UUID%%> \\n backing-store %%NEW_LOGVOL_PATH%% \\n </target>"',
                                        '/etc/stratuslab/iscsi.conf' ],
                    'check':[ '/usr/bin/test', '-b', '%%LOGVOL_PATH%%' ],
                    'create':[ '/sbin/lvcreate', '-L', '%%SIZE%%G', '-n', '%%UUID%%', '%%VOLUME_NAME%%' ],
                    'dmremove':['/sbin/dmsetup', 'remove', '%%LOGVOL_PATH%%'],
                    'getturl' : ['/bin/echo', 'iscsi://%%ISCSI_HOST%%/iqn.2011-01.eu.stratuslab:%%UUID%%:1' ],
                    'reload_iscsi': [ '/usr/sbin/tgt-admin', '--update', 'iqn.2011-01.eu.stratuslab:%%UUID%%'],
                    'reload_iscsi_snap': [ '/usr/sbin/tgt-admin', '--update', 'iqn.2011-01.eu.stratuslab:%%SNAP_UUID%%'],
                    'remove_device': [ '/bin/sed', '-i', '"/<target iqn.2011-01.eu.stratuslab:.*%%UUID%%.*/,+2d"', '/etc/stratuslab/iscsi.conf' ],
                    'remove':[ '/sbin/lvremove', '-f', '%%LOGVOL_PATH%%' ],
                    'rebase':[ '/bin/dd', 'if=%%LOGVOL_PATH%%', 'of=%%NEW_LOGVOL_PATH%%'],
                    # lvchange doesn't work with clone. Normally unneeded as lvremove -f (remove) does the same
                    'setinactive':[ '/sbin/lvchange', '-a', 'n', '%%LOGVOL_PATH%%' ],
                    'size':['/sbin/lvs', '-o', 'lv_size', '--noheadings', '%%LOGVOL_PATH%%'],
                    'snapshot':[ '/sbin/lvcreate', '--snapshot', '-p', 'rw', '--size', '%%SIZE%%G', '-n', '%%SNAP_UUID%%', '%%LOGVOL_PATH%%'  ],
                    'wait2':['/bin/sleep', '2'],
                    }
    
    backend_failure_cmds = {'remove': {'add_device' : [ 'sed', '-i', '"1i<target iqn.2011-01.eu.stratuslab:%%UUID%%> \\n backing-store %%LOGVOL_PATH%% \\n </target>"', '/etc/stratuslab/iscsi.conf' ]}
                                      # {'delete' : 'add_device'}
                            }
    
    success_msg_pattern = {'create':'Logical volume "[\w\-]+" created',
                           'remove':'Logical volume "[\w\-]+" successfully removed',
                           'rebase':'\d+ bytes .* copied',
                           'setinactive':[ '^$', 'File descriptor .* leaked on lvchange invocation' ],
                           'size':['([\d\.]+)g'],
                           'reload_iscsi':'.*',
                           'snapshot':'Logical volume "[\w\-]+" created',
                           'getturl' : '(.*://.*/.*)'
                          }
    
    new_lun_required = {'rebase':True
                        }
    
    def __init__(self, proxy, volume, mgtUser=None, mgtPrivKey=None, configHolder=ConfigHolder()):
        super(LVMBackend, self).__init__(configHolder)

        self.volumeName = volume
        self.proxyHost = proxy
        self.mgtUser = mgtUser
        self.mgtPrivKey = mgtPrivKey
        if self.mgtUser and self.mgtPrivKey:
            self.debug(1, 'SSH will be used to connect to %s backend' % self.getType())
            self.cmd_prefix = self.ssh_cmd_prefix
        else:
            self.cmd_prefix = [ ]
    
    
    # Parse all variables related to iSCSI proxy in the string passed as argument.
    # Return parsed string.
    def parse(self, string):
        if re.search('%%LOGVOL_PATH%%', string):
            string = re.sub('%%LOGVOL_PATH%%', self.volumeName + "/%%UUID%%", string)
        elif re.search('%%NEW_LOGVOL_PATH%%', string):
            string = re.sub('%%NEW_LOGVOL_PATH%%', self.volumeName + "/%%SNAP_UUID%%", string)
        return Backend.detokenize(self, string)
