#!/bin/sh -e

if [ -f /mnt/context.sh ]; then
  . /mnt/context.sh
fi

if [ -n "$IP_PRIVATE" ]; then
    ifconfig eth0 $IP_PRIVATE

    if [ -n "$PRIVATE_NETMASK" ]; then
        ifconfig eth0 netmask $PRIVATE_NETMASK
    fi
fi

if [ -n "$IP_PUBLIC" ]; then
	ifconfig eth1 $IP_PUBLIC

    if [ -n "$PUBLIC_NETMASK" ]; then
        ifconfig eth1 netmask $PUBLIC_NETMASK
    fi
fi

if [ -n "$IP_EXTRA" ]; then
	ifconfig eth2 $IP_EXTRA

    if [ -n "$EXTRA_NETMASK" ]; then
        ifconfig eth2 netmask $EXTRA_NETMASK
    fi
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
