#
# Created as part of the StratusLab project (http://stratuslab.eu),
# co-funded by the European Commission under the Grant Agreement
# INFSO-RI-261552."
#
# Copyright (c) 2011, GRNET S.A.
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
import unittest

from stratuslab.Runner import Runner
from stratuslab.ConfigHolder import ConfigHolder
from stratuslab.Cluster import Cluster

class ClusterTest(unittest.TestCase):
    instanceNumber = 2
    image = "JAm9q9vBzGJL1klVTe-9xBByfxj"
    instanceType = "c1.medium"
    userPublicKeyFile = None
    username = 'oneadmin'
    password = 'oneadmin'

    def testDeployNFSCluster(self):
        options = Runner.defaultRunOptions()
        options.update({'username': ClusterTest.username,
                        'password': ClusterTest.password,
                        'mpi_machine_file': True, 
                        'instanceType': self.instanceType, 
                        'noCheckImageUrl': False,
                        'cluster_admin': 'root', 
                        'cluster_user':'vangelis', 
                        'master_vmid': None,
                        'tolerate_failures': False, 
                        'clean_after_failure': False,
                        'include_master': True, 
                        'shared_folder':'/home', 
                        'useQcowDiskFormat': True,
                        'add_packages': None, 
                        'ssh_hostbased': False, 
                        'instanceNumber': self.instanceNumber,
                        'userPublicKeyFile': ClusterTest.userPublicKeyFile,
                        'verboseLevel':0, 
                        'marketplaceEndpoint':'http://marketplace.stratuslab.eu'})
        configHolder = ConfigHolder(options)
        runner = Runner(self.image, configHolder)
        cluster = Cluster(configHolder, runner, options['master_vmid'])
        runner.runInstance()

        self.assertTrue(cluster.deploy() in [0, 128])

        runner.killInstances(runner.vmIds)

    def testDeploySSHCluster(self):
        options = Runner.defaultRunOptions()
        options.update({'username': ClusterTest.username,
                        'password': ClusterTest.password,
                        'userPublicKeyFile': ClusterTest.userPublicKeyFile,
                        'mpi_machine_file': True, 
                        'instanceType': self.instanceType, 
                        'noCheckImageUrl': False,
                        'cluster_admin': 'root', 
                        'cluster_user':'vangelis', 
                        'master_vmid': None,
                        'tolerate_failures': False, 
                        'clean_after_failure': False,
                        'include_master': True, 
                        'shared_folder': None, 
                        'useQcowDiskFormat': True,
                        'add_packages': None, 
                        'ssh_hostbased': True, 
                        'instanceNumber': self.instanceNumber,
                        'verboseLevel':0, 
                        'marketplaceEndpoint':'http://marketplace.stratuslab.eu'})
        configHolder = ConfigHolder(options)
        runner = Runner(self.image, configHolder)
        cluster = Cluster(configHolder, runner, options['master_vmid'])
        runner.runInstance()
        
        self.assertTrue(cluster.deploy() in [0, 128])

        runner.killInstances(runner.vmIds)

    def testHeterogeneousCluster(self):
        # Master node instance
        options = Runner.defaultRunOptions()
        options.update({'username': ClusterTest.username,
                        'password': ClusterTest.password,
                        'userPublicKeyFile': ClusterTest.userPublicKeyFile,
                        'useQcowDiskFormat': True, 
                        'noCheckImageUrl': False,
                        'instanceType': 'm1.large', 
                        'instanceNumber': 1, 
                        'verboseLevel':0,
                        'marketplaceEndpoint':'http://marketplace.stratuslab.eu'})
        configHolder = ConfigHolder(options)
        runner = Runner(self.image, configHolder)
        runner.runInstance()

        masterId = runner.vmIds

        # Worker node instance
        options.update({'username': ClusterTest.username,
                        'password': ClusterTest.password,
                        'userPublicKeyFile': ClusterTest.userPublicKeyFile,
                        'mpi_machine_file': True, 
                        'instanceType': self.instanceType, 
                        'noCheckImageUrl': False,
                        'cluster_admin': 'root', 
                        'cluster_user':'vangelis', 
                        'master_vmid': runner.vmIds[0],
                        'include_master': True, 
                        'shared_folder': '/home', 
                        'useQcowDiskFormat': True,
                        'tolerate_failures': False, 
                        'clean_after_failure': False,
                        'add_packages': None, 
                        'ssh_hostbased': False, 
                        'instanceNumber': self.instanceNumber-1,
                        'verboseLevel':0, 
                        'marketplaceEndpoint':'http://marketplace.stratuslab.eu'})
        configHolder = ConfigHolder(options)
        runner = Runner(self.image, configHolder)
        cluster = Cluster(configHolder, runner, options['master_vmid'])
        runner.runInstance()

        self.assertTrue(cluster.deploy() in [0, 128])

        runner.killInstances(masterId)
        runner.killInstances(runner.vmIds)

if __name__ == "__main__":
    unittest.main()

