import os
import shutil
import subprocess
import glob
from datetime import datetime
from subprocess import *

from stratuslab.FileAppender import FileAppender
from stratuslab.Util import fileGetContent
from stratuslab.Util import filePutContent
from stratuslab.Util import getSystemMethods
from stratuslab.Util import modulePath
from stratuslab.Util import printAction
from stratuslab.Util import printError
from stratuslab.Util import printStep
from stratuslab.Util import execute
from stratuslab.Util import appendOrReplaceInFile

class CreateBaseImage(object):
    
    def __init__(self, options):
        self.options = options

        self.imageSize = options.imageSize
        self.swap = options.swap
        self.swapSize = options.swapSize
        self.loopDev = options.loopDev
        self.os = options.os
        self.osVersion = options.osVersion
        self.arch = options.arch
        self.imageVersion = options.imageVersion
        self.outputDir = options.outputDir
        self.mountDir = options.mountDir
        self.rootPasswd = options.rootPasswd
        self.publicKey = options.publicKey
        self.debug = options.debug
        self.type = options.type
        self.createTime = datetime.now().isoformat(' ')
        self.debian = options.debian
        self.ubuntu = options.ubuntu
        self.mirror = options.mirror
        self.qtrProfile = options.qtrProfile
       
        dateNow = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        if not (self.debug):
            self.stdout = open('/tmp/stratuslab_%s.log' % dateNow, 'a')
            self.stderr = open('/tmp/stratuslab_%s.err' % dateNow, 'a')
        else:
            self.stdout = sys.stdout
            self.stderr = sys.stderr

        if (self.debian):
            if (self.arch == 'i386'):
                self.kernelArch = '686'
            elif (self.arch == 'i686'):
                self.kernelArch = '686'
            elif (self.arch == 'amd64'):
                self.kernelArch = 'amd64'
            elif (self.arch == 'x86_64'):
                self.kernelArch = 'amd64'
            else:
                self.kernelArch = self.arch
        elif (self.ubuntu):
            if (self.arch == 'i386'):
                self.kernelArch = '386'
            elif (self.arch == 'i686'):
                self.kernelArch = '686'
            elif (self.arch == 'amd64'):
                self.kernelArch = 'amd64-server'
            else:
                self.kernelArch = self.arch
        else: 
           if (self.arch == 'i686'):
               self.rinseArch = 'i386'
           elif (self.arch == 'x86_64'):
               self.rinseArch = 'amd64'
           else:
               self.rinseArch = self.arch

        baseName = '%s-%s-%s-%s' % (self.os, self.osVersion, self.arch, self.type)
        fullOutputDir = '%s/%s/%s/%s' % (self.outputDir, self.type.replace('.','/'), baseName, self.imageVersion)
        self.outputDir = fullOutputDir

        self.outputFileName = '%s-%s.img' % (baseName, self.imageVersion)
        self.realRoot = os.open("/", os.O_RDONLY)        
        self.inRoot = False

        if not self.publicKey is None:
            self.publicKeyContent = fileGetContent(self.publicKey)

    def createImage(self):
        self._createDiskImage()
        self._installOS()
        self._installGrub()
        self._installContext()  
        self._installGrid()
        self._createManifest()
         
    def __del__(self):
        if(self.inRoot):
        	self._chrootExit()
        self._cleanup()
        
        if not (self.debug):
            self.stderr.close()
            self.stdout.close()

    def _createDiskImage(self):
        printAction('Creating disk image.')
        printStep('Creating empty disk image %s.' % self.outputFileName)
        if not os.path.exists(self.outputDir):
            os.makedirs(self.outputDir)

        self._execute(['/bin/dd','if=/dev/zero','of=%s/%s' % (self.outputDir, self.outputFileName)
                     ,'bs=1M','count=1','seek=%d' % self.imageSize])

        printStep('Creating partitions.')

        if (self.swap):
            printStep('Creating %sMB swap space.' % self.swapSize)
            rootSize = self.imageSize - self.swapSize
            sfDiskString = ',%d,83,*\n,,82\n' % rootSize
        else:
            sfDiskString = ',,83,*\n'

        p = subprocess.Popen(['/sbin/sfdisk','-uM','%s/%s' % (self.outputDir, self.outputFileName)], 
                              stdout=PIPE, stdin=PIPE, stderr=self.stderr)
        stdout = p.communicate(input='%s' % sfDiskString)[0]

        printStep('Creating loop devices and mapper.')
        self._execute(['/sbin/losetup',self.loopDev,'%s/%s' % (self.outputDir, self.outputFileName)])
        self._execute(['/sbin/kpartx','-a',self.loopDev])

        printStep('Making filesystem.')
        path,dev = os.path.split(self.options.loopDev)
        self.loopDevMapper = '/dev/mapper/%s' % dev

        self._execute(['/sbin/mkfs.ext3','%sp1' % self.loopDevMapper])
        p = subprocess.Popen(['/sbin/blkid','-o','value','%sp1' % self.loopDevMapper], stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        uuid = stdout.split();
        self.root_uuid = uuid[0]

        p = subprocess.Popen(['/sbin/mkswap','%sp2' % self.loopDevMapper], stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        s_uuid = stdout.split('UUID=');
        self.swap_uuid = s_uuid[1].strip();

    def _installOS(self):
        printAction('Installing base operating system.')
        if not os.path.exists(self.mountDir):
            os.makedirs(self.mountDir)

        self._execute(['/bin/mount',self.loopDevMapper + "p1",self.mountDir])

        if (self.debian):
            self._installOSDebian()
        elif (self.ubuntu):
            self._installOSUbuntu()
        else:
            self._installOSRedhat()
                        
        #setup networking
        hosts = open('%s/etc/hosts' % self.mountDir, 'w')
        hosts.write("127.0.0.1  localhost localhost.localdomain");
        hosts.close()

        #chroot to target
        self._chroot()

        #setup access
        if not self.rootPasswd is None:
            printStep('Setting root password.')
            self._execute(['/usr/sbin/usermod','-p','%s' % self.rootPasswd,'root'])

        if not self.publicKey is None:
            printStep('Installing SSH key.')
            if not os.path.exists('/root/.ssh'):
                os.makedirs('/root/.ssh')
            filePutContent('/root/.ssh/authorized_keys', self.publicKeyContent)
            self._execute(['/bin/chmod','-R','600','/root/.ssh/'])

        self._chrootExit()

    def _installOSRedhat(self):
        self._execute(['/usr/sbin/rinse','--arch=%s' % self.rinseArch,'--distribution','%s-%s' % (self.os, self.osVersion),
                           '--directory',self.mountDir,'--post-install','/bin/true'])
 
        #fix yum
        self._searchreplace('%s/etc/yum.repos.d/*.repo' % self.mountDir, '$basearch', self.arch)

        if not os.path.exists('%s/usr/lib/python2.4/site-packages/urlgrabber.skx' % self.mountDir):
            os.makedirs('%s/usr/lib/python2.4/site-packages/urlgrabber.skx' % self.mountDir)

        for filename in glob.glob1('%s/usr/lib/python2.4/site-packages/urlgrabber' % self.mountDir,'keepalive.*'):
            srcfile = os.path.join('%s/usr/lib/python2.4/site-packages/urlgrabber' % self.mountDir,
                                    filename)
            destfile = os.path.join('%s/usr/lib/python2.4/site-packages/urlgrabber.skx' % self.mountDir,
                                    filename)
            shutil.move(srcfile, destfile)

        printStep('Installing extra packages.')
        self._execute(['/bin/mount','-o','bind','/proc','%s/proc' % self.mountDir])
        shutil.copy('/etc/resolv.conf','%s/etc/resolv.conf' % self.mountDir)

        self._chroot()
        self._execute(['/usr/bin/yum','install','-y','yum'])
        self._execute(['/usr/bin/yum','install','-y','vim-enhanced','less','bzip2'
                                                   ,'openssh-server','rsync'
                                                   ,'gnupg', 'perl','man'])
        self._execute(['/usr/bin/yum','install','-y','kernel'])
        self._execute(['/usr/bin/yum','install','-y','grub'])

        for file in glob.glob('/usr/share/grub/%s-redhat/*' % self.arch):
            shutil.copy(file, '/boot/grub')

        self._chrootExit()
        
        # networking
        ifcfg = open('%s/etc/sysconfig/network-scripts/ifcfg-eth0' % self.mountDir, 'w')
        ifcfg.write("DEVICE=eth0\nBOOTPROTO=dhcp\nONBOOT=yes")
        ifcfg.close()

        network = open('%s/etc/sysconfig/network' % self.mountDir, 'w')
        network.write("NETWORKING=yes\nHOSTNAME=localhost.localdomain\n")
        network.close()

        #clean up
        rpm_files = '%s/*.rpm' % self.mountDir
        rpms = glob.glob(rpm_files)
        for r in rpms:
            os.remove(r)

    def _installOSDebian(self):
        self._execute(['/usr/sbin/debootstrap', '--arch=%s' % self.arch, self.osVersion, self.mountDir, self.mirror])
        
        printStep('Installing extra packages.')
        self._chroot()

        kernel_img_conf = open('/etc/kernel-img.conf', 'wb')
        kernel_img_conf.write('do_symlinks = yes\n'
                              'relative_links = yes\n'
                              'do_bootfloppy = no\n'
                              'do_initrd = yes\n'
                              'link_in_boot = no\n'
                              'postinst_hook = update-grub\n'
                              'postrm_hook = update-grub\n'
                              'do_bootloader = no\n')
        kernel_img_conf.close()
        
        self._execute(['apt-get', 'install', '-y', '--force-yes', 'grub'])
        self._execute(['apt-get', 'install', '-y', '--force-yes', 'linux-image-%s' % self.kernelArch],
                      False, True, False)
        self._execute(['apt-get', 'install', '-y', '--force-yes', 'ssh'],
                       False, True, False)

        os.makedirs('/boot/grub')
        for file in glob.glob('/usr/lib/grub/%s-pc/*' % self.arch):
            shutil.copy(file, '/boot/grub')

        self._chrootExit()

        # networking
        ifcfg = open('%s/etc/network/interfaces' % self.mountDir, 'w')
        ifcfg.write("auto eth0\niface eth0 inet dhcp\n")
        ifcfg.close()

        hostname = open('%s/etc/hostname' % self.mountDir, 'w')
        hostname.write("localhost")
        hostname.close()

    def _installOSUbuntu(self):
        self._execute(['/usr/sbin/debootstrap', '--arch=%s' % self.arch, self.osVersion, self.mountDir, self.mirror])

        printStep('Installing extra packages.')
        self._chroot()

        kernel_img_conf = open('/etc/kernel-img.conf', 'wb')
        kernel_img_conf.write('do_symlinks = yes\n'
                              'relative_links = yes\n'
                              'do_bootfloppy = no\n'
                              'do_initrd = yes\n'
                              'link_in_boot = no\n'
                              'do_bootloader = no\n')
        kernel_img_conf.close()

        self._execute(['dpkg-divert','--local','--rename','--add','/sbin/initctl'])
        self._execute(['ln','-s','/bin/true','/sbin/initctl'])
        
        self._execute(['apt-get', 'install', '-y', '--force-yes', 'grub'])
        self._execute(['apt-get', 'install', '-y', '--force-yes', 'linux-image-%s' % self.kernelArch],
                      False, True, False)
        self._execute(['apt-get', 'install', '-y', '--force-yes', 'ssh'],
                       False, True, False)

        if not os.path.exists('/boot/grub'):
            os.makedirs('/boot/grub')

        for file in glob.glob('/usr/lib/grub/%s-pc/*' % self.arch):
            shutil.copy(file, '/boot/grub')

        self._execute(['rm','/sbin/initctl']) 
        self._execute(['dpkg-divert','--local','--remove','/sbin/initctl'])

        self._chrootExit()

        # networking
        ifcfg = open('%s/etc/network/interfaces' % self.mountDir, 'w')
        ifcfg.write("auto eth0\niface eth0 inet dhcp\n")
        ifcfg.close()

        hostname = open('%s/etc/hostname' % self.mountDir, 'w')
        hostname.write("localhost")
        hostname.close()

    def _installGrub(self):
        if (self.debian):
            self._installGrubDebian()
        elif (self.ubuntu):
            self._installGrubUbuntu()
        else:
            self._installGrubRedhat()

    def _installGrubRedhat(self):
        printAction('Installing Grub (RedHat).')
        self._execute(['/bin/mount','-o','bind','/dev','%s/dev' % self.mountDir])

        device_map = open('%s/device.map' % self.outputDir, 'w')
        device_map.write('(hd0) %s/%s\n' % (self.outputDir, self.outputFileName))
        device_map.close()

        t_device_map = open('%s/boot/grub/device.map' % self.mountDir, 'w')
        t_device_map.write('(hd0) %s\n(hd0,0) %sp1\n' % (self.loopDev,self.loopDevMapper))
        t_device_map.close()

        self._execute(['/sbin/grub-install','--root-directory=%s' % self.mountDir,self.loopDev],
                     False,True,False)

        p = subprocess.Popen(['/sbin/grub','--device-map=%s/device.map' % self.outputDir], 
                              stdout=PIPE, stdin=PIPE, stderr=self.stderr)
        stdout = p.communicate(input='root (hd0,0)\nsetup (hd0)\nquit\n')[0]

        t_device_map = open('%s/boot/grub/device.map' % self.mountDir, 'w')
        t_device_map.write('(hd0) UUID=%s\n' % self.root_uuid)
        t_device_map.close()

        kernelVersion = ''

        for filename in os.listdir("%s/boot" % self.mountDir):
             if (filename.startswith("vmlinuz")):
                kernelVersion = filename.split("-", 1)[1]

        grub_conf = open('%s/boot/grub/grub.conf' % self.mountDir, 'w')
        grub_conf.write('default=0\ntimeout=5\n\ntitle %s %s (%s)\n'
                        '\troot (hd0,0)\n'
                        '\tkernel /boot/vmlinuz-%s root=UUID=%s ro\n'
                        '\tinitrd /boot/initrd-%s.img\n' % (self.os, self.osVersion, kernelVersion, kernelVersion, self.root_uuid, kernelVersion))
        grub_conf.close()
        
        fstab = open('%s/etc/fstab' % self.options.mountDir, 'w')
        fstab.write("UUID=%s / ext3 defaults 1 1\n"
                    "proc /proc proc defaults 0 0\n"
                    "UUID=%s swap swap defaults 0 0\n" % (self.root_uuid, self.swap_uuid))
        fstab.close()

        self._chroot()
        self._execute(['/sbin/mkinitrd','-f','/boot/initrd-%s.img' % kernelVersion, kernelVersion],False,True,False)
        self._chrootExit()

        #remove created file
        os.remove(os.path.join(self.outputDir, 'device.map'))

    def _installGrubDebian(self):
        printAction('Installing Grub (Debian).')
        self._execute(['/bin/mount','-o','bind','/dev','%s/dev' % self.mountDir])

        device_map = open('%s/device.map' % self.outputDir, 'w')
        device_map.write('(hd0) %s/%s\n' % (self.outputDir, self.outputFileName))
        device_map.close()
       
        self._execute(['/sbin/grub-install','--root-directory=%s' % self.mountDir,self.loopDev],
                     False,True,False)
 
        p = subprocess.Popen(['/sbin/grub','--device-map=%s/device.map' % self.outputDir],
                              stdout=PIPE, stdin=PIPE, stderr=self.stderr)
        stdout = p.communicate(input='root (hd0,0)\nsetup (hd0)\nquit\n')[0]

        t_device_map = open('%s/boot/grub/device.map' % self.mountDir, 'w')
        t_device_map.write('(hd0) UUID=%s\n' % self.root_uuid)
        t_device_map.close()

        self._chroot()
        self._execute(['update-grub'])
        self._chrootExit()

        self._searchreplace('%s/boot/grub/menu.lst' % self.mountDir, '%sp1' % self.loopDevMapper, 'UUID=%s' % self.root_uuid)
        self._searchreplace('%s/boot/grub/menu.lst' % self.mountDir, '%sp1' % os.path.basename(self.loopDev), 'hd0,0')
        
        os.chdir('%s/boot/grub' % self.mountDir)
        os.symlink('menu.lst', 'grub.conf')
        os.fchdir(self.realRoot)

        self._chroot()
        self._execute(['update-grub'])
        self._chrootExit()        

        fstab = open('%s/etc/fstab' % self.options.mountDir, 'w')
        fstab.write("UUID=%s / ext3 defaults 1 1\n"
                    "proc /proc proc defaults 0 0\n"
                    "UUID=%s swap swap defaults 0 0\n" % (self.root_uuid, self.swap_uuid))
        fstab.close()
        
        #remove created file
        os.remove(os.path.join(self.outputDir, 'device.map'))
  
    def _installGrubUbuntu(self):
        printAction('Installing Grub (Ubuntu).')
        self._execute(['/bin/mount','-o','bind','/dev','%s/dev' % self.mountDir])
        self._execute(['/bin/mount','-o','bind','/dev/pts','%s/dev/pts' % self.mountDir])

        device_map = open('%s/device.map' % self.outputDir, 'w')
        device_map.write('(hd0) %s/%s\n' % (self.outputDir, self.outputFileName))
        device_map.close()

        self._execute(['/sbin/grub-install','--root-directory=%s' % self.mountDir,self.loopDev],
                     False,True,False)

        p = subprocess.Popen(['/sbin/grub','--device-map=%s/device.map' % self.outputDir],
                              stdout=PIPE, stdin=PIPE, stderr=self.stderr)
        stdout = p.communicate(input='root (hd0,0)\nsetup (hd0)\nquit\n')[0]

        t_device_map = open('%s/boot/grub/device.map' % self.mountDir, 'w')
        t_device_map.write('(hd0) UUID=%s\n' % self.root_uuid)
        t_device_map.close()

        self._chroot()
        self._execute(['update-grub','-y'])
        self._chrootExit()

        if os.path.exists('%s/boot/grub/menu.lst' % self.mountDir):
            self._searchreplace('%s/boot/grub/menu.lst' % self.mountDir, '=root=/dev/hda1', '=root=UUID=%s' % self.root_uuid)
            self._searchreplace('%s/boot/grub/menu.lst' % self.mountDir, '%sp1' % os.path.basename(self.loopDev), 'hd0,0')
            self._searchreplace('%s/boot/grub/menu.lst' % self.mountDir, 'defoptions=quiet splash', 'defoptions= ')

            os.chdir('%s/boot/grub' % self.mountDir)
            os.symlink('menu.lst', 'grub.conf')
            os.fchdir(self.realRoot)

        self._chroot()
        self._execute(['update-grub','-y'])
        self._chrootExit()

        fstab = open('%s/etc/fstab' % self.options.mountDir, 'w')
        fstab.write("UUID=%s / ext3 defaults 1 1\n"
                    "proc /proc proc defaults 0 0\n"
                    "UUID=%s swap swap defaults 0 0\n" % (self.root_uuid, self.swap_uuid))
        fstab.close()

        #remove created file
        os.remove(os.path.join(self.outputDir, 'device.map'))
        self._execute(['/bin/umount','%s/dev/pts' % self.mountDir], False, True, False)

    def _installContext(self):
        printAction('Installing contextualisation.')

        filePutContent('%s/usr/bin/onecontext' % self.mountDir,"#!/bin/sh -e\n\n"
                         "[ -e /dev/hdc ] && DEVICE=hdc || DEVICE=sr0\n\n"
                         "mount -t iso9660 /dev/$DEVICE /mnt\n\n"
                         "if [ -f /mnt/context.sh ]; then\n"
                         "\t. /mnt/init.sh\n"
                         "fi\n"
                         "umount /mnt\n\n"
                         "exit 0\n")
        appender = FileAppender(os.path.join(os.sep, self.mountDir, 'etc', 'rc.local'))
        contextScript = 'bash /usr/bin/onecontext'
        appender.insertAtTheEnd(contextScript)

    def _installGrid(self):
        if (self.type == 'base.quattor'):
            self._installQuattor()
        
        if (self.type == 'grid.wn'):
            self._installGridNode('glite-WN')
 
    def _installQuattor(self):
        printAction('Installing Quattor client.')

        installScript = fileGetContent('%s/share/creation/quattor-client-install.sh' % modulePath)
        filePutContent('%s/tmp/quattor-client-install.sh' % self.mountDir, installScript)
        filePutContent('%s/etc/ccm.conf' % self.mountDir, "profile\t\t %s\n" % self.qtrProfile)        

        #fix yum
        self._searchreplace('%s/etc/yum.repos.d/dag.repo' % self.mountDir, 'enabled=0', 'enabled=1')

        self._chroot()
        self._execute(['/usr/bin/yum','install','-y','perl-Crypt-SSLeay','perl-XML-Parser'
                       ,'perl-IO-String','perl-Proc-ProcessTable','perl-DBI','perl-libwww-perl'])
        self._execute(['bash','/tmp/quattor-client-install.sh'])
        self._execute(['/usr/sbin/ccm-initialise'])
        self._chrootExit()        

        os.remove(os.path.join(self.mountDir, 'tmp/quattor-client-install.sh'))

    def _installGridNode(self, nodeType):
        printAction('Installing %s node.' % nodeType)

        self._execute(['curl','http://grid-deployment.web.cern.ch/grid-deployment/glite/repos/3.2/%s.repo' % nodeType,
                      '-o','%s/etc/yum.repos.d/%s.repo' % (self.mountDir, nodeType)])
        #fix yum
        self._searchreplace('%s/etc/yum.repos.d/dag.repo' % self.mountDir, 'enabled=0', 'enabled=1')

        self._chroot()
        self._execute(['/usr/bin/yum','install','-y','gcc'])
        self._execute(['/usr/bin/yum','groupinstall','-y',nodeType])
        self._chrootExit()

    def _createManifest(self):
        printAction('Creating manifest file.')
        manifest = fileGetContent('%s/share/template/manifest.xml.tpl' % modulePath)
        manifest = manifest % {'created': self.createTime,
                               'type': self.type,
                               'version': self.imageVersion,
                               'arch': self.arch,
                               'user': os.environ['USER'],
                               'os': self.os,
                               'osversion': self.osVersion
                              }
        filePutContent('%s/%s.manifest.xml' % (self.outputDir, self.outputFileName), manifest)           

    def _cleanup(self):
        if os.path.exists('%s/dev' % self.mountDir):
            self._execute(['/bin/umount','%s/dev' % self.mountDir], False, True, False)
        
        if os.path.exists('%s/proc' % self.mountDir):
	    self._execute(['/bin/umount','%s/proc' % self.mountDir], False, True, False)

        if(os.path.ismount(self.mountDir)):
            self._execute(['/bin/umount','%s' % self.mountDir], False, True, False)
        
        if os.path.exists(self.loopDev):
            self._execute(['/sbin/kpartx','-d',self.loopDev], False, True, False)
            self._execute(['/sbin/losetup','-d',self.loopDev], False, True, False)

    def _chroot(self):
        os.chroot(self.mountDir)
        os.chdir('/')
        self.inRoot = True

    def _chrootExit(self):
        os.fchdir(self.realRoot)
        os.chroot(".")
        self.inRoot = False

    def _searchreplace(self, path, search, replace):
       import fileinput, glob, string, sys, os
       from os.path import join
       # replace a string in multiple files
       #filesearch.py

       files = glob.glob(path)
       if files is not []:
           for file in files:
               for line in fileinput.input(file,inplace=1):
                   lineno = 0
                   lineno = string.find(line, search)
                   if lineno >= 0:
                       line = line.replace(search, replace)
                   sys.stdout.write(line)

    def _execute(self, command, shell=False, wait=True, exitOnError=True):
        #print command
        process = subprocess.Popen(command, shell=shell, stdout=self.stdout, stderr=self.stderr)
        if wait:
            process.wait()
            if process.returncode != 0 and exitOnError:
                printError('Command failed: %s' % ' '.join(command))
