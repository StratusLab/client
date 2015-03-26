
from .Backend import Backend

def getBackendProxy(config):
    backend_attributes = {'volume_name': ''}
    proxy_name = config.get_proxy_name()
    config.set_backend_proxy_attributes(backend_attributes, proxy_name)

    return GPFSBackend(proxy_name,
                       backend_attributes['mgt_user_name'],
                       backend_attributes['mgt_user_private_key'],
                       backend_attributes['volume_name'])

class GPFSBackend(Backend):
    """
    This backend manages persistent disks on a GPFS filesystem. It
    relies on some advanced features provided by GPFS like cloning.

    WARNING: this backend only works with systems configured for english
             language (e.g. en_US.UTF-8).
    """

    _type = 'GPFS'

    mmclone_bin = '/usr/lpp/mmfs/bin/mmclone'

    lun_backend_cmd_mapping = {
        'check': ['check'],
        'create': ['create'],
        'delete': ['delete'],
        'getturl': ['getturl'],
        'map': [],
        'rebase': ['mmclonesplit'],
        'size': [],
        'snapshot': ['mmclonesnap', 'mmclonecopy'],
        'unmap': [],
    }

    backend_cmds = {
        'check': ['/usr/bin/test', '-f', '%%LOGVOL_PATH%%'],
        'create': ['/bin/dd', 'if=/dev/zero', 'of=%%LOGVOL_PATH%%', 'bs=1024', 'count=%%SIZE%%M'],
        'chown': ['/bin/chown', 'oneadmin:cloud', '%%LOGVOL_PATH%%'],
        'delete': ['/bin/rm', '%%LOGVOL_PATH%%'],
        'getturl': ['/bin/echo', 'file://%%LOGVOL_PATH%%'],
        'mmclonesnap': [mmclone_bin, 'snap', '%%LOGVOL_PATH%%'],
        'mmclonecopy': [mmclone_bin, 'copy', '%%LOGVOL_PATH%%', '%%NEW_LOGVOL_PATH%%'],
        'mmclonesplit': [mmclone_bin, 'split', '%%LOGVOL_PATH%%'],
        'mmcloneredirect': [mmclone_bin, 'redirect', '%%LOGVOL_PATH%%'],
        'mmcloneshow': [mmclone_bin, 'show', '%%LOGVOL_PATH%%'],
    }

    failure_ok_msg_pattern = {
        'mmclonesnap': ['^mmclone: Read-only file system'],
    }

    success_msg_pattern = {
        'create': '.*',
        'getturl': '(file://.*)',
    }

    def __init__(self, proxyHost, mgtUser, mgtPrivKey, volume):
        super(GPFSBackend, self).__init__()

        self.proxyHost = proxyHost
        self.mgtUser = mgtUser
        self.mgtPrivKey = mgtPrivKey
        self.volumeName = volume

        if self.mgtUser and self.mgtPrivKey:
            self.debug(1, 'SSH will be used to connect to %s backend.' % self.getType())
            self.cmd_prefix = self.ssh_cmd_prefix
        else:
            self.cmd_prefix = []

    def detokenize(self, string):
        string = string.replace('%%LOGVOL_PATH%%', self.volumeName + "/%%UUID%%")
        string = string.replace('%%NEW_LOGVOL_PATH%%', self.volumeName + "/%%SNAP_UUID%%")
        return super(GPFSBackend, self).detokenize(string)

