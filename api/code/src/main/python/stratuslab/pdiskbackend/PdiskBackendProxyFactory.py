from stratuslab.Util import loadModule
from stratuslab.pdiskbackend.utils import abort

backend_modules = {'lvm' : 'LVMBackend',
                   'ceph' : 'CephBackend',
                   'file' : 'FileBackend',
                   'netapp' : 'NetAppBackend',
                   'netapp-7mode' : 'NetAppBackend',
                   'netapp-cluster' : 'NetAppBackend'}

supported_proxy_types = backend_modules.keys()

backends_package_path = 'stratuslab.pdiskbackend.backends'

def get_backend_proxy_module_name(config):
    backend_type = config.get_backend_type(config.get_proxy_name()).lower()
    try:
        return backends_package_path + '.' + backend_modules[backend_type]
    except KeyError:
        abort("Unsupported back-end type '%s' (supported types: %s)" %\
                                (backend_type, ','.join(supported_proxy_types)))

class PdiskBackendProxyFactory(object):
    @staticmethod
    def createBackendProxy(configHolder):
        return loadModule(get_backend_proxy_module_name(configHolder)).\
            getBackendProxy(configHolder)
