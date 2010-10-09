#!/bin/sh -e

source /mnt/context.sh

mkdir -p /root/.ssh
echo "$PUBLIC_KEY" >> /root/.ssh/authorized_keys
chmod -R 600 /root/.ssh/

INTERNAL_KEY=/mnt/internal_key.pub
if [ -f "$INTERNAL_KEY" ]; then
    more "$INTERNAL_KEY" >> /root/.ssh/authorized_keys
fi
