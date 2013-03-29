#!/bin/bash

PACKAGES=$*

if [ "x$PACKAGES" = "x" ]; then
    exit 0
fi

function get_package_manager() {
    if [ "x$(type -a apt-get | grep is)" != "x" ]; then
        UPDATE_CMD="apt-get update"
        INSTALL_CMD="apt-get install -y"
    elif [ "x$(type -a yum | grep is)" != "x" ]; then 
        UPDATE_CMD=""
        INSTALL_CMD="yum install -y"
    else
        echo "Unable to find a package manager. Aborting"
        exit 1
    fi
}

function install_packages() {
    $UPDATE_CMD
    $INSTALL_CMD $PACKAGES
    EXIT_CODE=$?
}

# Lauch install
get_package_manager
install_packages

exit $EXIT_CODE