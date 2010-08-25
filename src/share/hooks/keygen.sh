#!/bin/bash

KEY_NAME="$1"

[ "x$KEY_NAME" = "x" ] && exit 0

ssh-keygen -f $KEY_NAME -N "" -q
