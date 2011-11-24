###########################################
# General
###########################################

# Disk sharing: iscsi or nfs 
disk.store.share=%(persistent_disk_share)s
# How many user can read a disk at the same time
disk.store.user_per_disk=1
# Cloud node private key file (for hotplug)
disk.store.cloud.node.ssh_keyfile=/opt/stratuslab/storage/pdisk/cloud_node.key
# User that we should use to log on the node (for hotplug)
disk.store.cloud.node.admin=%(one_username)s
# Cloud VM directory on node (for hotplug)
disk.store.cloud.node.vm_dir=/var/lib/one
# Username of storage service
disk.store.cloud.service.user=pdisk

###########################################
# NFS
###########################################

disk.store.nfs.location=/mnt/pdisk

###########################################
# iSCSI
###########################################

# How the disk are created: block file (file) or LVM volume (lvm)
disk.store.iscsi.type=%(persistent_disk_storage)s
# Where to store bloc file if used. Else see LVM section
disk.store.iscsi.file.location=/mnt/pdisk
disk.store.iscsi.conf=/etc/tgt/targets.conf
disk.store.iscsi.admin=/usr/sbin/tgt-admin

###########################################
# LVM
###########################################

disk.store.lvm.device=/dev/vg.02
disk.store.lvm.vgdisplay=/sbin/vgdisplay
disk.store.lvm.create=/sbin/lvcreate
disk.store.lvm.remove=/sbin/lvremove
disk.store.lvm.lvchange=/sbin/lvchange
disk.store.lvm.dmsetup=/sbin/dmsetup

###########################################
# Zookeeper
###########################################

# Comma separated host:port pairs, each corresponding to a zk
# server. e.g. "127.0.0.1:3000,127.0.0.1:3001,127.0.0.1:3002" If
# the optional chroot suffix is used the example would look
# like: "127.0.0.1:3000,127.0.0.1:3001,127.0.0.1:3002/app/a"
# where the client would be rooted at "/app/a" and all paths
# would be relative to this root - ie getting/setting/etc...
# "/foo/bar" would result in operations being run on
# "/app/a/foo/bar" (from the server perspective).
disk.store.zookeeper.address=127.0.0.1:2181