
import re

from .Backend import Backend
from stratuslab.pdiskbackend.ConfigHolder import ConfigHolder

def getBackendProxy(config):
    backend_attributes = {'volume_name':''}
    proxy_name = config.get_proxy_name()
    config.set_backend_proxy_attributes(backend_attributes, proxy_name)

    return FileBackend(proxy_name,
                       backend_attributes['volume_name'],
                       config,
                       mgtUser=backend_attributes['mgt_user_name'],
                       mgtPrivKey=backend_attributes['mgt_user_private_key'])

class FileBackend(Backend):
    
    _type = 'file'
    
    # The following variables define which command to execute for each action.
    # They are documented in the superclass Backend
    
    lun_backend_cmd_mapping = {'check':['check'],
                               'create':['create', 'chown'],
                               'delete':['delete'],
                               'getturl':['getturl'],
                               'map':[],
                               'rebase':[],
                               'size':[],
                               'snapshot':['copy'],
                               'unmap':[],
                               }
    
    backend_cmds = {'check':['/usr/bin/test', '-f', '%%LOGVOL_PATH%%'],
                    'chown' :['/bin/chown', 'oneadmin:cloud', '%%LOGVOL_PATH%%'],
                    'copy':['/bin/cp', '%%LOGVOL_PATH%%', '%%NEW_LOGVOL_PATH%%'],
                    'create':['/bin/dd', 'if=/dev/zero', 'of=%%LOGVOL_PATH%%', 'bs=1024', 'count=%%SIZE%%M'],
                    'delete':['/bin/rm', '-rf', '%%LOGVOL_PATH%%'],
                    'getturl':['/bin/echo', 'file://%%LOGVOL_PATH%%'],
                    }
    
    success_msg_pattern = {'create' : '.*',
                           'getturl' : '(.*://.*)',
                           }
    def __init__(self, proxy, volume, configHolder, mgtUser=None, mgtPrivKey=None):
        super(FileBackend, self).__init__(configHolder)

        self.volumeName = volume
        self.proxyHost = proxy
        self.mgtUser = mgtUser
        self.mgtPrivKey = mgtPrivKey
        if self.mgtUser and self.mgtPrivKey:
            self.debug(1, 'SSH will be used to connect to %s backend' % self.getType())
            self.cmd_prefix = self.ssh_cmd_prefix
        else:
            self.cmd_prefix = []
    
    # Parse all variables related to iSCSI proxy in the string passed as argument.
    # Return parsed string.
    def detokenize(self, string):
        if re.search('%%LOGVOL_PATH%%', string):
            string = re.sub('%%LOGVOL_PATH%%', self.volumeName + "/%%UUID%%", string)
        elif re.search('%%NEW_LOGVOL_PATH%%', string):
            string = re.sub('%%NEW_LOGVOL_PATH%%', self.volumeName + "/%%SNAP_UUID%%", string)
        return super(FileBackend, self).detokenize(string)
