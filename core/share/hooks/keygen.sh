#!/bin/bash

KEY_NAME="$1"

[ -d $KEY_NAME ] && exit 0

mkdir -p `dirname $KEY_NAME`

ssh-keygen -f $KEY_NAME -N "" -q
