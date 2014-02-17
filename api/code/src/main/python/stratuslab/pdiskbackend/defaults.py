VERBOSITY = 0
CONFIG_FILE_NAME = '/etc/stratuslab/pdisk-backend.cfg'
CONFIG_MAIN_SECTION = 'main'
CONFIG_LOG_DIRECTION = 'console'
CONFIG_DEFAULTS = """
# Options commented out are configuration options available for which no 
# sensible default value can be defined.
[%(section_main)s]
# Define the list of iSCSI proxies that can be used.
# One section per proxy must also exists to define parameters specific to the proxy.
#iscsi_proxies=netapp.example.org
# Log direction: console or syslog
log_direction=%(log_direction)s
# User name to use to connect the filer (may also be defined in the filer section)
mgt_user_name=root
# SSH private key to use for 'mgt_user_name' authorisation
#mgt_user_private_key=/some/file.rsa

#[netapp.example.org]
# iSCSI back-end type (case insensitive)
#type=NetApp
# Initiator group the LUN must be mapped to
#initiator_group = linux_servers
# Name appended to the volume name to build the LUN path (a / will be appended)
#lun_namespace=stratuslab
# Volume name where LUNs will be created
#volume_name = /vol/iscsi
# Name prefix to use to build the volume snapshot used as a LUN clone snapshot parent
# (a _ will be appended)
#volume_snapshot_prefix=pdisk_clone

#[lvm.example.org]
# iSCSI back-end type (case insensitive)
#type=LVM
# LVM volume group to use for creating LUNs
#volume_name = /dev/iscsi.01

#[ceph.example.org]
#type=ceph
# Define default Ceph monitor endpoints. Use proxy host and default port if
# empty.
#monitors=host-mon1:6789,host-mon2:6789,
# Define the identity to authenticate the host/user.
#identity=cloud
# Define the Ceph pool where RBD images are stored.
#pool_name=cloud
# Define the base name for snapshots.
#snapshot_name=base
""" % {'section_main' : CONFIG_MAIN_SECTION,
       'log_direction' : CONFIG_LOG_DIRECTION}
