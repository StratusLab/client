###########################################
# General
###########################################

# Disk sharing: iscsi or file
#disk.store.share=%(persistent_disk_share)s

# How the disk are created: block file (file) or LVM volume (lvm)
#disk.store.iscsi.type=%(persistent_disk_storage)s

# Cloud node private key file (for hotplug)
disk.store.cloud.node.ssh_keyfile=/opt/stratuslab/storage/pdisk/cloud_node.key

# User that we should use to log on the node (for hotplug)
disk.store.cloud.node.admin=%(one_username)s

# Cloud VM directory on node (for hotplug)
disk.store.cloud.node.vm_dir=/var/lib/one

# Username of storage service
disk.store.cloud.service.user=pdisk

# Sections for pdisk-backend.cfg config file
# These are active if set in the configuration
# parameter disk.backend.sections.names
disk.backend.sections = %(persistent_disk_backend_sections)s

# Active backends in pdisk-backend.cfg
disk.backend.sections.names = %(persistent_disk_backend_sections_names)s

###########################################
# NFS
###########################################

disk.store.nfs.location=%(persistent_disk_nfs_mount_point)s

###########################################
# LVM
###########################################

disk.store.lvm.device=%(persistent_disk_lvm_device)s
