import os
import stratuslab.Util as Util


def getInstance(system, options = {}):
    if not os.path.isfile('%s/%s.py' % (Util.systemsDir, system)):
        raise ValueError('Specified system %s not available' % system)

    Util.setPythonPath(Util.systemsDir)

    module = Util.importSystem(system)

    obj = getattr(module, 'system')
    Util.assignAttributes(obj, options)
    
    return obj
