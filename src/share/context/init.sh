#!/bin/sh -e

source /mnt/context.sh
source /mnt/configuration.sh

ifconfig eth0 ${IP_PRIVATE}${NETMASK_PRIVATE}

route add -net ${GLOBAL_NETWORK}/${GLOBAL_NETMASK} dev eth0

route add default gw ${DEFAULT_GATEWAY} dev eth0

if [ -n "$IP_PUBLIC" ]; then
    ifconfig eth1 ${IP_PUBLIC}${NETMASK_PUBLIC}
    route add default gw ${DEFAULT_GATEWAY} dev eth1
fi

if [ -n "$IP_EXTRA" ]; then
    ifconfig eth2 ${IP_EXTRA}${NETMASK_EXTRA}
    route add default gw ${DEFAULT_GATEWAY} dev eth2
fi

mkdir -p /root/.ssh
echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
chmod -R 600 /root/.ssh/

if [ -n "$STRATUSLAB_REMOTE_KEY" ]; then
    echo "$STRATUSLAB_REMOTE_KEY" >> /root/.ssh/authorized_keys
fi

# OpenDNS server
echo "nameserver 208.67.222.222" > /etc/resolv.conf
echo "nameserver 208.67.220.220" >> /etc/resolv.conf
