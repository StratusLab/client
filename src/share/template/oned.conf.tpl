#*******************************************************************************
#             OpenNebula Configuration file (Stratuslab version)
#*******************************************************************************

#*******************************************************************************
# Daemon configuration attributes
#-------------------------------------------------------------------------------
#  HOST_MONITORING_INTERVAL: Time in seconds between host monitorization
#
#  VM_POLLING_INTERVAL: Time in seconds between virtual machine monitorization.
#  (use 0 to disable VM monitoring).
#
#  VM_DIR: Remote path to store the VM images, it should be shared between all
#  the cluster nodes to perform live migrations. This variable is the default
#  for all the hosts in the cluster.
#
#  PORT: Port where oned will listen for xmlrpc calls.
#
#  DB: Configuration attributes for the database backend
#   backend : can be sqlite or mysql (default is sqlite)
#   server  : (mysql) host name or an IP address for the MySQL server
#   user    : (mysql) user's MySQL login ID
#   passwd  : (mysql) the password for user
#   db_name : (mysql) the database name
#
#  VNC_BASE_PORT: VNC ports for VMs can be automatically set to VNC_BASE_PORT +
#  VMID
#
#  DEBUG_LEVEL: 0 = ERROR, 1 = WARNING, 2 = INFO, 3 = DEBUG
#*******************************************************************************

HOST_MONITORING_INTERVAL = %(host_monitoring_interval)s

VM_POLLING_INTERVAL      = %(vm_polling_interval)s

VM_DIR=%(vm_dir)s 

PORT=%(one_port)s

# TODO: Add value in config
DB = [ backend = "sqlite" ]

# Sample configuration for MySQL
# DB = [ backend = "mysql",
#        server  = "localhost",
#        user    = "oneadmin",
#        passwd  = "oneadmin",
#        db_name = "opennebula" ]

VNC_BASE_PORT = %(vnc_base_port)s

DEBUG_LEVEL=%(debug_level)s

#*******************************************************************************
# Physical Networks configuration
#*******************************************************************************
#  NETWORK_SIZE: Here you can define the default size for the virtual networks
#
#  MAC_PREFIX: Default MAC prefix to be used to create the auto-generated MAC
#  addresses is defined here (this can be overrided by the Virtual Network
#  template)
#*******************************************************************************

NETWORK_SIZE = %(network_size)s

MAC_PREFIX   = %(mac_prefix)s

#*******************************************************************************
# Information Driver Configuration
#*******************************************************************************
# You can add more information managers with different configurations but make
# sure it has different names.
#
#   name      : name for this information manager
#
#   executable: path of the information driver executable, can be an
#               absolsute path or relative to $ONE_LOCATION/lib/mads (or
#               /usr/lib/one/mads/ if OpenNebula was installed in /)
#
#   arguments : for the driver executable, usually a probe configuration file,
#               can be an absolute path or relative to $ONE_LOCATION/etc (or
#               /etc/one/ if OpenNebula was installed in /)
#*******************************************************************************


#-------------------------------------------------------------------------------
#  XEN Information Driver Manager sample configuration
#-------------------------------------------------------------------------------
IM_MAD = [
    name       = "im_xen",
    executable = "one_im_ssh",
    arguments  = "im_xen/im_xen.conf" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#  KVM Information Driver Manager sample configuration
#-------------------------------------------------------------------------------
IM_MAD = [
      name       = "im_kvm",
      executable = "one_im_ssh",
      arguments  = "im_kvm/im_kvm.conf" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#  EC2 Information Driver Manager sample configuration
#-------------------------------------------------------------------------------
#IM_MAD = [
#      name       = "im_ec2",
#      executable = "one_im_ec2",
#      arguments  = "im_ec2/im_ec2.conf" ]
#-------------------------------------------------------------------------------

#*******************************************************************************
# Virtualization Driver Configuration
#*******************************************************************************
# You can add more virtualization managers with different configurations but
# make sure it has different names.
#
#   name      : name of the virtual machine manager driver
#
#   executable: path of the virtualization driver executable, can be an
#               absolute path or relative to $ONE_LOCATION/lib/mads (or
#               /usr/lib/one/mads/ if OpenNebula was installed in /)
#
#   arguments : for the driver executable
#
#   default   : default values and configuration parameters for the driver, can
#               be an absolute path or relative to $ONE_LOCATION/etc (or
#               /etc/one/ if OpenNebula was installed in /)
#
#   type      : driver type, supported drivers: xen, kvm, xml
#*******************************************************************************

#-------------------------------------------------------------------------------
#  XEN Virtualization Driver Manager sample configuration
#-------------------------------------------------------------------------------
VM_MAD = [
    name       = "vmm_xen",
    executable = "one_vmm_xen",
    default    = "vmm_xen/vmm_xen.conf",
    type       = "xen" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#  KVM Virtualization Driver Manager sample configuration
#-------------------------------------------------------------------------------
VM_MAD = [
    name       = "vmm_kvm",
    executable = "one_vmm_kvm",
    default    = "vmm_kvm/vmm_kvm.conf",
    type       = "kvm" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
#  EC2 Virtualization Driver Manager sample configuration
#    arguments: default values for the EC2 driver, can be an absolute path or
#               relative to $ONE_LOCATION/etc (or /etc/one/ if OpenNebula was
#               installed in /).
#-------------------------------------------------------------------------------
#VM_MAD = [
#    name       = "vmm_ec2",
#    executable = "one_vmm_ec2",
#    arguments  = "vmm_ec2/vmm_ec2.conf",
#    type       = "xml" ]
#-------------------------------------------------------------------------------

#*******************************************************************************
# Transfer Manager Driver Configuration
#*******************************************************************************
# You can add more transfer managers with different configurations but make
# sure it has different names.
#   name      : name for this transfer driver
#
#   executable: path of the transfer driver executable, can be an
#               absolute path or relative to $ONE_LOCATION/lib/mads (or
#               /usr/lib/one/mads/ if OpenNebula was installed in /)
#
#   arguments : for the driver executable, usually a commands configuration file
#               , can be an absolute path or relative to $ONE_LOCATION/etc (or
#               /etc/one/ if OpenNebula was insta%(hypervisor)slled in /)
#*******************************************************************************

#-------------------------------------------------------------------------------
# SSH Transfer Manager Driver sample configuration
#-------------------------------------------------------------------------------
TM_MAD = [
    name       = "tm_ssh",
    executable = "one_tm",
    arguments  = "tm_ssh/tm_ssh.conf" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# NFS Transfer Manager Driver sample configuration
#-------------------------------------------------------------------------------
TM_MAD = [
    name       = "tm_nfs",
    executable = "one_tm",
    arguments  = "tm_nfs/tm_nfs.conf" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# Dummy Transfer Manager Driver sample configuration
#-------------------------------------------------------------------------------
TM_MAD = [
    name       = "tm_dummy",
    executable = "one_tm",
    arguments  = "tm_dummy/tm_dummy.conf" ]
#-------------------------------------------------------------------------------

#-------------------------------------------------------------------------------
# LVM Transfer Manager Driver sample configuration
#-------------------------------------------------------------------------------
TM_MAD = [
    name       = "tm_lvm",
    executable = "one_tm",
    arguments  = "tm_lvm/tm_lvm.conf" ]
#-------------------------------------------------------------------------------

#*******************************************************************************
# Hook Manager Configuration
#*******************************************************************************
# The Driver (HM_MAD), used to execute the Hooks
#   executable: path of the hook driver executable, can be an
#               absolute path or relative to $ONE_LOCATION/lib/mads (or
#               /usr/lib/one/mads/ if OpenNebula was installed in /)
#
#   arguments : for the driver executable, can be an absolute path or relative
#               to $ONE_LOCATION/etc (or /etc/one/ if OpenNebula was installed
#               in /)
#
# Virtual Machine Hooks (VM_HOOK) defined by:
#   name      : for the hook, useful to track the hook (OPTIONAL)
#   on        : when the hook should be executed,
#               - CREATE, when the VM is created (onevm create)
#               - RUNNING, after the VM is successfully booted
#               - SHUTDOWN, after the VM is shutdown
#               - STOP, after the VM is stopped (including VM image transfers)
#               - DONE, after the VM is deleted or shutdown
#   command   : use absolute path here
#   arguments : for the hook. You can access to VM template variables with $
#               - $ATTR, the value of an attribute e.g. $NAME or $VMID
#               - $ATTR[VAR], the value of a vector e.g. $NIC[MAC]
#               - $ATTR[VAR, COND], same of previous but COND select between
#                 multiple ATTRs e.g. $NIC[MAC, NETWORK="Public"]
#   remote    : values,
#               - YES, The hook is executed in the host where the VM was
#                 allocated
#               - NO, The hook is executed in the OpenNebula server (default)
#-------------------------------------------------------------------------------

HM_MAD = [
    executable = "one_hm" ]

VM_HOOK = [
    name      = "keygen",
    on        = "create",
    command   = "%(one_home)s/share/hooks/keygen.sh",
    arguments = "$CONTEXT[STRATUSLAB_SSH_KEY]",
    remote    = "yes" ]

VM_HOOK = [
    name      = "upload",
    on        = "shutdown",
    command   = "%(one_home)s/share/hooks/upload",
    arguments = "%s(vm_dir)s/$VMID/images/disk.0 $NIC[network="private"] $CONTEXT[STRATUSLAB_SSH_KEY] $CONTEXT[STRATUSLAB_CREATE_IMAGE]",
    remote    = "yes" ]
