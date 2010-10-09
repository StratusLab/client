import os
import stratuslab.Util as Util

def getSystem(system, configHolder):
    moduleDir = os.path.dirname(__file__)

    if not os.path.isfile('%s/%s.py' % (moduleDir, system)):
        raise ValueError('Failed to find system module %s' % system)

    Util.setPythonPath(moduleDir)

    module = Util.importSystem(system)

    obj = getattr(module, 'system')
    configHolder.assign(obj)
    obj.init()
    
    return obj
