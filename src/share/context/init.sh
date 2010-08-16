#!/bin/sh -e

source /mnt/context.sh

ifconfig eth0 ${IP_PRIVATE}/${NETMASK_PRIVATE}
route add -net ${NETWORK_PRIVATE}/${NETMASK_PRIVATE} dev eth0

if [ -n "$IP_PUBLIC" ]; then
    ifconfig eth1 ${IP_PUBLIC}/${NETMASK_PUBLIC}
    route add -net ${NETWORK_PUBLIC}/${NETMASK_PUBLIC} dev eth1
fi

if [ -n "$IP_EXTRA" ]; then
    ifconfig eth2 ${IP_EXTRA}/${NETMASK_EXTRA}
    route add -net ${NETWORK_EXTRA}/${NETMASK_EXTRA} dev eth2
fi

if [ -f /mnt/$ROOT_PUBKEY ]; then
	mkdir -p /root/.ssh
	cat /mnt/$ROOT_PUBKEY >> /root/.ssh/authorized_keys
	chmod -R 600 /root/.ssh/
fi

if [ -n "$USERNAME" ]; then
	useradd $USERNAME
	if [ -f /mnt/$USER_PUBKEY ]; then
		mkdir -p /home/$USERNAME/.ssh/
		cat /mnt/$USER_PUBKEY >> /home/$USERNAME/.ssh/authorized_keys
		chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh
		chmod -R 600 /home/$USERNAME/.ssh/authorized_keys
	fi
fi

