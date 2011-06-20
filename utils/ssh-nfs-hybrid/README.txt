ssh_nfs_hybrid_patch v0.1 
---------------------------

General
-------
This patch fixes a number of issues with StratusLab performance when VM Containers do not have enough disk to support 'ssh' StratusLab mode and where storage is provided through nfs or other shared filesystem (has been tested with glusterfs as well). 'nfs' nodes are predictably slow, since nfs does not scale well, even in medium installations (i.e. 10 VM containers or more). This patch offers ssh performance with nfs storage backend.

Assumptions
-----------
- Currently, this patch assumes that the shared filesystem is mounted on /var/lib/one/ebs/. This should be fixed in later versions to $ONE_LOCATION/ebs. THIS FUNCTION IS NOT PROVIDED FROM STRATUS_INSTALL. It is the admin's responsibility to mount it on all VM containers and the Frontend (through /etc/fstab/).
- It assumes that stratus-install was run with type 'ssh' for all nodes.

Limitations
-----------
- It provides extra disks and backing images through nfs. User images are created on the fly with qemu-img create -b <backing_image_on_nfs> /<path>/disk.0. If nfs becomes unresponsive, running images will be affected. This might be a bug or a feature, depending on the networking and nfs infrastructure (i.e. how much do you trust your nfs mounts?).
- It has been tested and works on StratusLab v.0.4. Future releases probably won't break it, but no testing has been done (obviously...).
- Extra disks are still slow on writes (since they are running on nfs). However, users can work around that by processing their data and writing in chunks on the much faster local image disk (mounted under /).
- The cache never expires. It also depends on the filename. It works with marketplace images, but there should be an expiration mechanism (preferably based on md5sum?).

Installation
------------
Simply copy tm_clone.sh and tm_mkimage.sh to $ONE_LOACTION/lib/tm_commands/ssh/ and scripts_common.sh to $ONE_LOACTION/lib/sh/ overwriting the existing ones. Preferably, backup the existing scripts. No restart is required.

Gains
-----
- Extremely fast instantiation (under 10 secs for cached images)
- Solves storage space problems on nodes
- Solves performance bottleneck on writes to disk

How it works
------------
- When an image is requested, we test to see if the image already exists on nfs cache, based on its file name / LOCATION for marketplace images. If that is not the case, we download it, extract it if needed and place it in cache.
- Then, an image is created, backed by the cached image, and placed on the node where OpenNebula expects it. That's all!
- Extra disks are created on the nfs share and then a soft link is created where OpenNebula expects the image. This might seem dangerous, but KVM takes care of this enventuality with a little help from the linux kernel.