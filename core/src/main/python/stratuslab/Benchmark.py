import datetime
import inspect
import os
import time
import unittest
import urllib2

from stratuslab.Runner import Runner
from stratuslab.Exceptions import NetworkException, OneException
from stratuslab.Exceptions import ConfigurationException
from stratuslab.Exceptions import ExecutionException
from stratuslab.Exceptions import InputException
from stratuslab.ConfigHolder import ConfigHolder
import Util
from stratuslab.Util import sshCmd
from stratuslab.Util import scp
from stratuslab.Util import sshCmdWithOutput
VM_START_TIMEOUT = 5 * 60 # 5 min

class Benchmark(object):
    

    def __init__(self, runner, configHolder,vmId):
        configHolder.assign(self)
        self._runner = runner
        self.vmId = vmId
        self.output_xml=''
        self.cpustresstime='600'
        self.io_i='10'
        self.io_o='10'

    def run(self):
        allocatedIp = self.prepareMachine(self.vmId)
        vm_cpu, vm_ram, vm_swap = self._runner.getInstanceType().get(self._runner.instanceType)
        if self.output_folder:
            self.output_xml=self.output_folder
        else:
            self.output_xml='/tmp'


  
        if self.openmp:  
            self.openmp_benchmark(allocatedIp,vm_cpu,self._runner.userPrivateKeyFile)      
        if self.io:
            self.io_benchmark(allocatedIp,vm_cpu,self._runner.userPrivateKeyFile)
        if self.cpu_intensive:
            self.cpu_benchmark(allocatedIp,vm_cpu,self._runner.userPrivateKeyFile)
        if self.workflows:
            self.workflow_benchmark(allocatedIp,vm_cpu,self._runner.userPrivateKeyFile)
        if self.mpi:
            self.mpi_benchmark(allocatedIp,vm_cpu,self._runner.userPrivateKeyFile)
        if self.all:
            self.all_benchmarks(allocatedIp,vm_cpu,self._runner.userPrivateKeyFile)
        
        self._stopVm(self.vmId)       
        
            


    def openmp_benchmark(self,ip_vm,vm_cpu,sshkey):
        executables=['openmp-jacobi','openmp-cg','openmp-matrix']
        for executable in executables:
            cmd = executable + ' ' + str(vm_cpu)
            self.run_scenario(cmd,ip_vm,sshkey)


    def io_benchmark(self,ip_vm,vm_cpu,sshkey):
        executables=['io-mpi-o','io-mpi-i','io-mpi-io']
        for executable in executables:
            cmd = executable + ' ' + str(vm_cpu) + ' ' + self.io_i + ' ' + self.io_o
            print "cmdio=", cmd
            self.run_scenario(cmd,ip_vm,sshkey)

    def cpu_benchmark(self,ip_vm,vm_cpu,sshkey):
        executable = 'cpu_intensive' + ' ' + str(vm_cpu) + ' ' + self.cpustresstime 
        self.run_scenario(executable,ip_vm,sshkey)

    def workflow_benchmark(self,ip_vm,vm_cpu,sshkey):
        executable = 'kepler-nogui /root/KeplerData/MyData/matrix_workflow.xml'
        self.run_scenario(executable,ip_vm,sshkey)

    def mpi_benchmark(self,ip_vm,vm_cpu,sshkey):
        executables=['mpi-standard']
        self.create_machine_file(ip_vm, vm_cpu, '/tmp/hostfile')
        
        scp('/tmp/hostfile','root@%s:'%ip_vm,sshkey)
        os.unlink('/tmp/hostfile')        
        for executable in executables:
            cmd = executable + ' ' + '/root/hostfile' + ' ' + str(vm_cpu)
            self.run_scenario(cmd,ip_vm,sshkey)


    def run_scenario(self,cmd,ip_vm,sshkey):
        sshCmdWithOutput(cmd,ip_vm,sshkey)
        script='/root/*.xml'
        destination=self.output_xml
        scp('root@%s:%s' % (ip_vm,script),destination,sshkey)

    def all_benchmarks(self,ip_vm,vm_cpu,sshkey):
        self.openmp_benchmark(ip_vm,vm_cpu,sshkey)
        self.mpi_benchmark(ip_vm,vm_cpu,sshkey)        
        self.io_benchmark(ip_vm,vm_cpu,sshkey)
        self.workflow_benchmark(ip_vm,vm_cpu,sshkey)
        self.cpu_benchmark(ip_vm,vm_cpu,sshkey)

    def prepareMachine(self,vmId):
        vmStarted = self._runner.waitUntilVmRunningOrTimeout(vmId, VM_START_TIMEOUT)
        if not vmStarted:
            error = 'Failed to start VM id: %s' % vmId
            Util.printError(error, exit=False)
            raise OneException(error)

        _, allocatedIp = self._runner.getNetworkDetail(vmId)
        self._repeatCall(self._ping, self._runner)
        self._repeatCall(self._loginViaSsh, self._runner, '/bin/true')
        return allocatedIp

    def _ping(self, runner):

        _, ip = runner.getNetworkDetail(self.vmId)
        res = Util.ping(ip)
        if not res:
            raise ExecutionException('Failed to ping %s' % ip)

    def _loginViaSsh(self, runner, cmd):

        _, ip = runner.getNetworkDetail(self.vmId)
        res = Util.sshCmd(cmd, ip, runner.userPrivateKeyFile)
        if res:
            raise ExecutionException('Failed to SSH into machine for %s with return code %s' % (ip, res))

    def _stopVm(self, vmId):
        self._runner.cloud.vmKill(vmId)


    def _repeatCall(self, method, *args):
        numberOfRepetition = 60
        for _ in range(numberOfRepetition):
            failed = False
            try:
                if args:
                    method(*args)
                else:
                    method()
            except ExecutionException:
                failed = True
                time.sleep(10)
            else:
                break

        if failed:
            Util.printError('Failed executing method %s %s times, giving-up' % (method, numberOfRepetition), exit=False)
            raise

    def create_machine_file(self, vm_ip, vm_cpu, filename):
        mf = open(filename, "w")
        mf.write(vm_ip + " slots=" + str(vm_cpu) + "\n")
        mf.close()  
