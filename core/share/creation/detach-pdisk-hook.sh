#!/bin/bash

if [ "x$1" = "x" ]
then
    echo "usage: $0 VM_ID"
    exit 1
fi

VM_ID=$1
PDISK_FILE=/tmp/pdisk.$1

# Nothing to do if no pdik is mounted
[ -f $PDISK_FILE ] || exit 0

`cat $PDISK_FILE`

