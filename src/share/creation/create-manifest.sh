#!/bin/bash

ARGS="$*"
[ "x$ARGS" = "x" ] && exit 1 

SEPARATOR="$1"
IMAGE_TYPE="`echo "$ARGS" | cut -d $SEPARATOR -f2`"
IMAGE_VERSION="`echo "$ARGS" | cut -d $SEPARATOR -f3`"
USER="`echo "$ARGS" | cut -d $SEPARATOR -f4`"
MANIFEST_LOCATION="`echo "$ARGS" | cut -d $SEPARATOR -f5`"
CURRENT_TIME=`date --utc --rfc-2822`

function get_debian_system_info() {
    local INFO
    INFO=`cat /etc/lsb-release`
     
    OS=`echo "$INFO" | grep DISTRIB_ID | cut -d '=' -f2 | tr '[A-Z]' '[a-z]'`
    OSVERSION=`echo "$INFO" | grep DISTRIB_RELEASE | cut -d '=' -f2`
}

function get_redhat_system_info() {
    local INFO

    INFO=`cat /etc/redhat-release`

    OS=`echo "$INFO" | cut -d ' ' -f1 | tr '[A-Z]' '[a-z]'`
    OSVERSION=`echo "$INFO" | cut -d ' ' -f3`
}

function get_system() {
    if [ -f /etc/lsb-release ]; then
        get_debian_system_info
    elif [ -f /etc/redhat-release ]; then
        get_redhat_system_info
    fi
}

function get_arch() {
    ARCH=`uname -m`
}

function build_manifest() {
    mkdir -p `dirname $MANIFEST_LOCATION`

    cat >> $MANIFEST_LOCATION << EOF
<manifest>
    <created>$CURRENT_TIME</created>
    <type>$IMAGE_TYPE</type>
    <version>$IMAGE_VERSION</version>
    <arch>$ARCH</arch>
    <user>$USER</user>
    <os>$OS</os>
    <osversion>$OSVERSION</osversion>
</manifest>
EOF
}

# Do the job!
get_system
get_arch
build_manifest

