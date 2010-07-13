#!/usr/bin/env python

import os
import sys
import subprocess
from optparse import OptionParser

class StratusSimpleRun(object):
    '''A command line to install stratuslab on a remote host'''

    def __init__(self):
        self.rootPath = os.path.abspath('%s/../' %
            os.path.abspath(os.path.dirname(__file__)))
        usage = 'usage: %prog [options]'
        self.parser = OptionParser(usage=usage)

        self.parser.add_option('-n', '--nodes', dest='nodes',
            help='node list', default=['localhost'])
        self.parser.add_option('-p', '--port', dest='sshPort',
            help='ssh port of the frontend', default=22)
        self.parser.add_option('-k', '--key', dest='sshKey',
            help='ssh key to connect to the frontend',
            metavar='KEY_PATH',
            default=os.path.expandvars("$HOME/.ssh/root_hudson_id_rsa.key"))
        self.parser.add_option('--ssh-options', dest='sshOptions',
            default='-p %(sshPort)s -i %(sshKey)s', metavar='OPTIONS')
        self.parser.add_option('--scp-options', dest='scpOptions',
            default='-P %(sshPort)s -i %(sshKey)s -q -r',
            metavar='OPTIONS')
        self.parser.add_option('-f', '--frontend', dest='frontend',
            help='frontend endpoint', metavar='ENDPOINT',
            default='root@localhost')
        self.parser.add_option('-i', '--install-dir', metavar='PATH',
            dest='installDir', help='remote source directory',
            default='stratuslab') 

        (self.options, self.args) = self.parser.parse_args()

        sshSub = { 'sshPort': self.options.sshPort,
                   'sshKey': self.options.sshKey, }
        self.options.sshOptions = self.options.sshOptions % (sshSub)
        self.options.scpOptions = self.options.scpOptions % (sshSub)

        self.launchSimpleRun()
        
    def execute(self, command, shell=False, exitOnError=True):
    	process = subprocess.Popen(command, shell=shell)
        process.wait()
        if process.returncode != 0 and exitOnError:
            print 'Command failled: %s' % ' '.join(command)
            sys.exit(1)

    def ssh(self, command, shell=False, exitOnError=True):
        sshCmd = ['ssh']
        sshCmd.extend(self.options.sshOptions.split(' '))
        sshCmd.append(self.options.frontend)
        sshCmd.extend(command)
        self.execute(sshCmd, shell, exitOnError)

    def scp(self, src, dest):
        scpCmd ='scp %s %s %s' % (self.options.scpOptions, src, dest)
        self.execute(scpCmd.split(' '))

    def launchSimpleRun(self):
        print 'Multi-install workaround...'
        self.multiInstallWorkaround()
        print 'Upload stratuslab...'
        self.uploadStratuslab()
        print 'Configure stratuslab...'
        self.configureStratuslab()
        print 'Install stratuslab frontend...'
        self.installStratuslabFrontend()
        print 'Install stratuslab nodes...'
        self.installStratuslabNodes()

    def multiInstallWorkaround(self):
        self.ssh(['su', '-l', 'oneadmin', '-c', 'one stop'],
            exitOnError=False)
        self.ssh(['rm', '-rf', '/srv/cloud/one/*'], 
            exitOnError=False)
        self.ssh(['rm', '-rf', '/srv/cloud/one/.ssh'],
            exitOnError=False)

    def uploadStratuslab(self):
        self.ssh(['rm', '-rf', self.options.installDir])
        self.scp('%s/src/' % self.rootPath, '%s:%s' % (
            self.options.frontend, self.options.installDir))

    def configureStratuslab(self):
        self.ssh(['python', '%s/stratus-config.py' 
            % self.options.installDir, '-r'])
        self.ssh(['python', '%s/stratus-config.py' 
            % self.options.installDir])

    def installStratuslabFrontend(self):
        self.ssh(['python', '%s/stratus-install.py' 
            % self.options.installDir])

    def installStratuslabNodes(self):
        for node in nodes:
            self.ssh(['python', '%s/stratus-install.py' 
                % self.options.installDir, '-n', node])


if __name__ == '__main__':
    try:
        StratusSimpleRun()
    except KeyboardInterrupt:
        print '\n\nExecution interrupted by the user... goodbye!'

