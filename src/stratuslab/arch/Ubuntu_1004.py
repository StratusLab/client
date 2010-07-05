# -*- coding: utf-8 -*-
from stratuslab.arch.Base import Base

class Ubuntu(Base):
    def __init__(self):
        self.os = 'Ubuntu 10.04'
        self.frontendDeps = [
            'ruby', 'libsqlite3-dev', 'libxmlrpc-c3-dev', 'libssl-dev',
            'scons', 'g++', 'git-core', 'ssh',
        ]
        self.NFSDeps = ['nfs-common']
        self.SSHDeps = []
        super(Base, self).__init__()

    def updatePackageManager(self):
        self.execute(['apt-get', 'update'])

    def installPackages(self, packages):
        self.execute(['apt-get', '-y', '-q',
        'install'].extend(packages)) 

machine = Ubuntu

