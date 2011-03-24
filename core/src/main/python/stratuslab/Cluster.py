#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2010-11, GRNET S.A.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.orgtex/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import time
import socket

from stratuslab.Util import printAction
from stratuslab.Util import printStep

class Host(object):
    
    def __init__(self):
        self.public_ip = None
        self.public_dns = None
        self.cores = None
        self.ram = None
        self.swap = None
        
class SSHUtil(object):
    _options = " -q -o StrictHostKeyChecking=no "
    _private_key = None
    _username = None
        
    def __init__(self, private_key, username):
        self._private_key = private_key
        self._username = username
        
    def copy_file_to_hosts(self, hostlist, file, remotepath): 
        cmd = "scp" + self._options + " -i " + self._private_key
    
        for host in hostlist:
            # print "Copying to host " + host.public_ip
            error = os.system(cmd + " " + file + " " + self._username + "@" + host.public_ip + ":" + remotepath)
            if error > 0 :
                print "Error while executing command"
                return error

        return 0
        
    def run_remote_command(self, hostlist, command):
        for host in hostlist:
            cmd = "ssh" + self._options + " -i " + self._private_key + " " + self._username + "@" + host.public_ip + " " + command
            # print "Command: " + cmd
            # print "Executing in host " + host.public_ip
            error = os.system(cmd)
            if error > 0 :
                print "Error while executing command"
                return error

        return 0
                
    def waitForConnectivity(self, host, timeout, attempts):
        additional_options = "-o ConnectTimeout=" + str(timeout) + " -o ConnectionAttempts=" + str(attempts)
        
        cmd = "ssh" + self._options + " " + additional_options + " -i " + self._private_key + " " + self._username + "@" + host.public_ip + " true"
        # print "Command: " + cmd
               
        attempts_counter = 0
        
        while True:
            error = os.system(cmd)
            
            if error >0 :
                if attempts_counter<attempts:
                    time.sleep(timeout)
                    attempts_counter += 1
                else:
                    return False
            else:
                return True        
    
class Cluster(object):

    hosts = []
    _is_heterogeneous = False

    def __init__(self, configHolder, runner, master_vmid):
        configHolder.assign(self)
        self._runner = runner
        if master_vmid:
            self._master_vmid=master_vmid
            self._is_heterogeneous=True

    def create_machine_file(self, hostlist, filename):
        mf = open(filename, "w")
        for host in hostlist:
            mf.write(host.public_ip + " slots=" + str(host.cores) + "\n")
        mf.close()
        

    def doAddPackages(self, ssh):
        # TODO: Add support for apt. Selection of package management system should be defined in the command line
        printStep('Installing additional software packages')
        packages = self.add_packages.replace(","," ")

        print "Trying to configure new apps with yum..."
        if ssh.run_remote_command(self.hosts, "yum -y install " + packages ):
            print "Trying to configure new apps with apt-get..."
            ssh.run_remote_command(self.hosts, "apt-get -q -y install " + packages )

    def doPrepareMPImachineFile(self, ssh, worker_nodes):
        # TODO: Let user choose where to place the machine file
        printStep('Preparing MPI machine file')
        target = []
        if self.include_master:
            target = self.hosts
        else:
            target = worker_nodes
        self.create_machine_file(target, "/tmp/machinefile")
        ssh.copy_file_to_hosts(self.hosts, "/tmp/machinefile", "/tmp")
        os.unlink("/tmp/machinefile")


    def doPrepareNFSSharedFolder(self, ssh, master_node, worker_nodes):
        printStep('Preparing NFS shared folder')
        master_only = []
        master_only.append(master_node)
        ssh.run_remote_command(self.hosts, "mkdir -p " + self.shared_folder)
        ssh.run_remote_command(master_only, "'echo " + self.shared_folder + " \"*(rw,no_root_squash)\" >> /etc/exports'")

        print "Trying RedHat configuration..."
        if ssh.run_remote_command(master_only, "service nfs restart"):
            print "Trying debian configuration..."
            ssh.run_remote_command(master_only, "service nfs-kernel-server restart")

        ssh.run_remote_command(worker_nodes, "mount " + master_node.public_ip + ":" + self.shared_folder + " " + self.shared_folder)


    def doSetupSSHHostBasedCluster(self, ssh, host):
        printStep('Configuring passwordless host-based ssh authentication')
        ssh.run_remote_command(self.hosts, "'echo \"IgnoreRhosts no\" >> /etc/ssh/sshd_config'")
        ssh.run_remote_command(self.hosts, "'echo \"HostbasedAuthentication yes\" >> /etc/ssh/sshd_config'")
        ssh.run_remote_command(self.hosts, "'echo \"HostbasedAuthentication yes\" >> /etc/ssh/ssh_config'")
        ssh.run_remote_command(self.hosts, "'echo \"EnableSSHKeysign yes\" >> /etc/ssh/ssh_config'")
        ssh.run_remote_command(self.hosts, "service sshd restart")
        for host in self.hosts:
            ssh.run_remote_command(self.hosts, "'ssh-keyscan -t rsa " + host.public_dns + " >> /etc/ssh/ssh_known_hosts'")


    def doCreateClusterUser(self, ssh, host, master_node):
        printStep('Creating additional user')
        master_only = []
        master_only.append(master_node)
        ssh.run_remote_command(self.hosts, "useradd -m " + self.cluster_user)
        ssh.run_remote_command(master_only, "mkdir /home/" + self.cluster_user + "/.ssh")
        ssh.run_remote_command(master_only, " \"ssh-keygen -q -t rsa -N '' -f /home/" + self.cluster_user + "/.ssh/id_rsa \"")
        ssh.run_remote_command(master_only, "cp /home/" + self.cluster_user + "/.ssh/id_rsa.pub /home/" + self.cluster_user + "/.ssh/authorized_keys")
        ssh.run_remote_command(master_only, "chown -R " + self.cluster_user + ":" + self.cluster_user + " /home/" + self.cluster_user + "/.ssh")
        if self.ssh_hostbased:
            for host in self.hosts:
                ssh.run_remote_command(self.hosts, "'echo " + host.public_dns + " " + self.cluster_user + " >> /home/" + self.cluster_user + "/.shosts'")


    def doUpdateEnvironmentVariables(self, ssh):
        printStep('Updating environment variables')
        counter = 0
        for node in self.hosts:
            target = []
            target.append(node)
            ssh.run_remote_command(target, "'echo export STRATUS_NC=" + str(counter) + " >> /etc/profile'")
            counter += 1


    def doUpdateHostsFile(self, ssh):
        printStep('Updating hosts file')
        ssh.run_remote_command(self.hosts, " 'echo  >> /etc/hosts'")
        ssh.run_remote_command(self.hosts, " 'echo \"# Cluster nodes\" >> /etc/hosts'")
        for host in self.hosts:
            ssh.run_remote_command(self.hosts, " 'echo " + host.public_ip + " " + host.public_dns + " >> /etc/hosts'")

    def deploy(self):
        ssh = SSHUtil(self._runner.userPrivateKeyFile, self.cluster_admin)
        
        # Wait until all the images are up and running     
        vmNetworkDetails = []
        vmStartTimeout = 600
        
        # wait until the each machine is up or timeout after 15 minutes
        print "Waiting for all cluster VMs to be instantiated"
        if self._is_heterogeneous:
            print "Waiting for master"
            self._runner.waitUntilVmRunningOrTimeout(self._master_vmid, vmStartTimeout)
            vmNetworkDetails.append(self._runner.getNetworkDetail(self._master_vmid))

        for vmId in self._runner.vmIds:
            #print "Waiting for instance to start running " + str(vmId)
            self._runner.waitUntilVmRunningOrTimeout(vmId, vmStartTimeout)
            vmNetworkDetails.append(self._runner.getNetworkDetail(vmId))
            
        vm_cpu, vm_ram, vm_swap = self._runner.getInstanceType().get(self._runner.instanceType)
        
        for vmNetwork in vmNetworkDetails:
            if vmNetwork[0] == 'public':
                host = Host()
                host.public_ip = vmNetwork[1]
                host.public_dns = socket.gethostbyaddr(host.public_ip)[0]
                host.cores = vm_cpu
                host.ram = vm_ram
                host.swap = vm_swap
                self.hosts.append(host)
                
        master_node = self.hosts[0]
        
        worker_nodes = list(self.hosts)
        
        worker_nodes.remove(master_node)
        
        print "\nMaster is " + master_node.public_dns
        
        for node in worker_nodes:
            print "Worker:" + node.public_dns
            
        print "Waiting for all instances to become accessible..."
        
        for host in self.hosts:
            hostready = False
            hostfailed = False
            
            while not hostready and not hostfailed:
                if not ssh.waitForConnectivity(host, 10, 30):
                    print "Timed out while connecting to " + host.public_ip
                    print "Removing from target configuration list"
                    self.hosts.remove(host)
                    hostfailed = True
                else:
                    hostready=True
            
        # Configure the hosts
        printAction('Configuring nodes')       
        
        # Try to install the missing packages
        if self.add_packages:
            self.doAddPackages(ssh)
                    
        # For MPI clusters prepare the machinefile for mpirun
        if self.mpi_machine_file:
            self.doPrepareMPImachineFile(ssh, worker_nodes)
        
        # Initialize the shared storage in NFS
        if self.shared_folder:
            self.doPrepareNFSSharedFolder(ssh, master_node, worker_nodes)
        
        if self.ssh_hostbased:
            self.doSetupSSHHostBasedCluster(ssh, host)
            
        if self.cluster_user:
            # Create a new user and prepare the environments for password-less ssh
            self.doCreateClusterUser(ssh, host, master_node)
                    
        # Update /etc/profile with StratusLab specific environment variables
        self.doUpdateEnvironmentVariables(ssh)
        
        # Update the /etc/hosts file for all hosts
        self.doUpdateHostsFile(ssh)
            

