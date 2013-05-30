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
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import socket
import time

from stratuslab.Util import printStep, printAction, printError, printInfo, printDebug


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

    def copy_file_to_hosts(self, hostlist, srcfile, remotepath):
        cmd = "scp" + self._options + " -i " + self._private_key

        for host in hostlist:
            printDebug('Copying to host %s' % host.public_ip)
            error = os.system(cmd + " " + srcfile + " " + self._username + "@" + host.public_ip + ":" + remotepath)
            if error > 0:
                return error

        return 0

    def run_remote_command(self, hostlist, command):
        for host in hostlist:
            cmd = "ssh -y" + self._options + " -i " + self._private_key + " " + \
                  self._username + "@" + host.public_ip + " " + command
            printDebug('Command: %s' % cmd)
            printDebug('Executing in host %s' % host.public_ip)
            error = os.system(cmd)
            if error > 0:
                return error

        return 0

    def waitForConnectivity(self, host, timeout):
        start_time = time.time()

        additional_options = "-o ConnectTimeout=10"

        cmd = "ssh" + self._options + " " + additional_options + " -i " + self._private_key + " " + \
              self._username + "@" + host.public_ip + " true"

        error = 1

        while (time.time() - start_time) < timeout and error > 0:
            error = os.system(cmd)

        if error > 0:
            return False
        else:
            return True


class Cluster(object):
    #hosts = []
    #_is_heterogeneous = False

    def __init__(self, configHolder, runner, master_vmid):
        configHolder.assign(self)
        self._runner = runner
        self.hosts = []
        self._is_heterogeneous = False
        if master_vmid:
            self._master_vmid = master_vmid
            self._is_heterogeneous = True

    def create_machine_file(self, hostlist, filename, isForMPI=False):
        mf = open(filename, "w")

        for host in hostlist:
            if isForMPI:
                additionalInfo = " slots=" + str(host.cores)
            else:
                additionalInfo = ""

            mf.write(host.public_ip + additionalInfo + "\n")
        mf.close()

    def doAddPackages(self, ssh):
        printStep('Installing additional software packages')
        packages = self.add_packages.replace(",", " ")

        printStep('Trying to configure new apps with yum...')
        if ssh.run_remote_command(self.hosts, "yum -q -y install " + packages):
            printStep('Trying to configure new apps with apt-get...')
            ssh.run_remote_command(self.hosts, "apt-get -q -y install " + packages)

    def doPrepareMPImachineFile(self, ssh, worker_nodes):
        printStep('Preparing MPI machine file')
        if self.include_master:
            target = self.hosts
        else:
            target = worker_nodes

        self.create_machine_file(target, "/tmp/machinefile", isForMPI=True)
        ssh.copy_file_to_hosts(self.hosts, "/tmp/machinefile", "/tmp")
        os.unlink("/tmp/machinefile")

    def doPrepareNodeList(self, ssh, worker_nodes):
        if self.include_master:
            target = self.hosts
        else:
            target = worker_nodes

        self.create_machine_file(target, "/tmp/cluster_nodelist")
        ssh.copy_file_to_hosts(self.hosts, "/tmp/cluster_nodelist", "/tmp")
        os.unlink("/tmp/cluster_nodelist")

    def doPrepareNFSSharedFolder(self, ssh, master_node, worker_nodes):
        printStep('Preparing NFS shared folder')
        master_only = []
        master_only.append(master_node)
        ssh.run_remote_command(self.hosts, "mkdir -p " + self.shared_folder)
        ssh.run_remote_command(master_only,
                               "'echo " + self.shared_folder + " \"*(rw,no_root_squash)\" >> /etc/exports'")

        printStep('\tTrying RedHat configuration...')
        if ssh.run_remote_command(master_only, "service nfs restart &> /dev/null"):
            printStep('\tTrying debian configuration...')
            ssh.run_remote_command(master_only, "service nfs-kernel-server restart &> /dev/null")

        ssh.run_remote_command(worker_nodes,
                               "mount " + master_node.public_ip + ":" + self.shared_folder + " " + self.shared_folder)

    def doSetupSSHHostBasedCluster(self, ssh):
        printStep('Configuring passwordless host-based ssh authentication')
        ssh.run_remote_command(self.hosts,
                               "'echo \"IgnoreRhosts no\" >> /etc/ssh/sshd_config && service sshd restart &> /dev/null && " +
                               "echo \"HostbasedAuthentication yes\n" +
                               "StrictHostKeyChecking no\n" +
                               "EnableSSHKeysign yes\" >> /etc/ssh/ssh_config'")

        for host in self.hosts:
            ssh.run_remote_command(self.hosts,
                                   "'ssh-keyscan -t rsa " + host.public_dns + " 2>/dev/null >> /etc/ssh/ssh_known_hosts && " \
                                                                              "echo " + host.public_dns + " root >> /root/.shosts'")

    def doCreateClusterUser(self, ssh, master_node):
        printStep('Creating additional user')
        master_only = []
        master_only.append(master_node)
        ssh.run_remote_command(self.hosts, "useradd -m " + self.cluster_user)
        ssh.run_remote_command(master_only,
                               ' "su - ' + self.cluster_user + " -c 'ssh-keygen -q -t rsa -N " + '\\"\\"' " -f ~/.ssh/id_rsa' " + '"')
        ssh.run_remote_command(master_only,
                               ' "su - ' + self.cluster_user + " -c 'cp ~/.ssh/id_rsa.pub ~/.ssh/authorized_keys' " + '"')

        #if self.shared_folder !="home":
        #    for host in self.hosts:
        #        ssh.run_remote_command(master_only, "scp -r /home/"+ self.cluster_user+"/.ssh " + host.public_ip + ":/home/" + self.cluster_user)

        if self.ssh_hostbased:
            for host in self.hosts:
                ssh.run_remote_command(self.hosts,
                                       ' "su - ' + self.cluster_user + " -c 'echo " + host.public_dns + " " + self.cluster_user + " >> ~/.shosts'" + '"')


    def doUpdateEnvironmentVariables(self, ssh, master_node, worker_nodes):
        printStep('Updating environment variables')
        active_nodes = []
        if self.include_master:
            active_nodes = self.hosts
        else:
            active_nodes = worker_nodes

        # Find the total available number of cores
        total_cores = 0
        for node in active_nodes:
            total_cores += int(node.cores)

        counter = 0
        for node in self.hosts:
            target = []
            target.append(node)
            ssh.run_remote_command(target, "'echo export STRATUSLAB_NC=" + str(
                counter) + " > /etc/profile.d/stratuslab_cluster.sh && " \
                           "echo export STRATUSLAB_CMASTER=" + master_node.public_dns + " >> /etc/profile.d/stratuslab_cluster.sh && " \
                                                                                        "echo export STRATUSLAB_CSIZE=" + str(
                len(active_nodes)) + " >> /etc/profile.d/stratuslab_cluster.sh && " \
                                     "echo export STRATUSLAB_CMAX_CORES=" + str(
                total_cores) + " >> /etc/profile.d/stratuslab_cluster.sh'")
            counter += 1


    def doUpdateHostsFile(self, ssh, master_node, worker_nodes):
        printStep('Updating hosts file')
        ssh.run_remote_command(self.hosts, "'echo  >> /etc/hosts && " \
                                           " echo \"# Cluster nodes\" >> /etc/hosts && " \
                                           " echo " + master_node.public_ip + " " + master_node.public_dns + " " + "master >> /etc/hosts'")

        counter = 0
        for host in worker_nodes:
            ssh.run_remote_command(self.hosts, " 'echo " + host.public_ip + " " + host.public_dns + " worker-" + str(
                counter) + " >> /etc/hosts'")
            counter += 1

    def doStartClusterServices(self, ssh, master_node):
        printStep("Applying user defined cluster services")
        master_only = []
        master_only.append(master_node)
        ssh.run_remote_command(master_only, "'if [ -e /etc/rc.cluster-services ]; then /etc/rc.cluster-services; fi'")

    def deploy(self):
        ssh = SSHUtil(self._runner.userPrivateKeyFile, self.cluster_admin)

        # Wait until all the images are up and running
        vmNetworkDetails = []
        vmStartTimeout = 600

        # wait until the each machine is up or timeout after 15 minutes
        printStep("Waiting for all cluster VMs to be instantiated...")
        if self._is_heterogeneous:
            printStep("Waiting for master")
            self._runner.waitUntilVmRunningOrTimeout(self._master_vmid, vmStartTimeout)
            vmNetworkDetails.append(self._runner.getNetworkDetail(self._master_vmid))

        for vmId in self._runner.vmIds:
            printDebug('Waiting for instance to start running %s' % str(vmId))
            self._runner.waitUntilVmRunningOrTimeout(vmId, vmStartTimeout)
            vmNetworkDetails.append(self._runner.getNetworkDetail(vmId))

        vm_cpu, vm_ram, vm_swap = self._runner.getInstanceResourceValues()

        for vmNetwork in vmNetworkDetails:
            if vmNetwork[0] == 'public':
                host = Host()
                host.public_ip = vmNetwork[1]

                try:
                    host.public_dns = socket.gethostbyaddr(host.public_ip)[0]
                except:
                    host.public_dns = host.public_ip

                host.cores = vm_cpu
                host.ram = vm_ram
                host.swap = vm_swap
                self.hosts.append(host)

        printStep("Waiting for all instances to become accessible...")

        failedHosts = []

        for host in self.hosts:
            hostReady = False
            hostFailed = False

            while not hostReady and not hostFailed:
                if not ssh.waitForConnectivity(host, vmStartTimeout):
                    printError('Timed out while connecting to %s.  Removing from target config. list.' % host.public_ip)
                    failedHosts.append(host)
                    hostFailed = True
                else:
                    hostReady = True

        if len(failedHosts) > 0:
            if self.tolerate_failures:
                for host in failedHosts:
                    self.hosts.remove(host)
            else:
                printError('Error instantiating some or all of the nodes. Bailing out...')
                if self.clean_after_failure:
                    self._runner.killInstances(self._runner.vmIds)
                return 128

        master_node = self.hosts[0]

        worker_nodes = list(self.hosts)

        worker_nodes.remove(master_node)

        printInfo('\tMaster is %s' % master_node.public_dns)

        for node in worker_nodes:
            printInfo('\tWorker: %s' % node.public_dns)

        # Configure the hosts
        printAction('Configuring nodes')

        # Try to install the missing packages
        if self.add_packages:
            self.doAddPackages(ssh)

        # For MPI clusters prepare the machinefile for mpirun
        if self.mpi_machine_file:
            self.doPrepareMPImachineFile(ssh, worker_nodes)

        if self.cluster_user:
            # Create a new user and prepare the environments for password-less ssh
            self.doCreateClusterUser(ssh, master_node)

        # Initialize the shared storage in NFS
        if self.shared_folder:
            self.doPrepareNFSSharedFolder(ssh, master_node, worker_nodes)

        if self.ssh_hostbased:
            self.doSetupSSHHostBasedCluster(ssh)

        # Update /etc/profile with StratusLab specific environment variables
        self.doUpdateEnvironmentVariables(ssh, master_node, worker_nodes)

        # Store the list of cluster nodes in a file under /tmp
        self.doPrepareNodeList(ssh, worker_nodes)

        # Update the /etc/hosts file for all hosts
        self.doUpdateHostsFile(ssh, master_node, worker_nodes)

        # Start any services defined in rc.cluster-services
        self.doStartClusterServices(ssh, master_node)

        return 0
