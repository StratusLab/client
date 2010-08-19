#! /bin/bash

VM_IMAGE=$1
VM_MANIFEST=$VM_IMAGE.manifest.xml
VM_IP=$2
KEY_NAME=$3

# Upload options
PROTOCOL=$4
APP_REPO=$5
COMPRESSION=$6
USERNAME=$7
PASSWORD=$8
[ "x$9" != "x" ] && FORCE_UPLOAD="--force"

[ "x$KEY_NAME" = "x" ] && exit 0


scp -i $KEY_NAME.pub root@$VM_IP:/tmp/stratuslab.manifest.xml $VM_MANIFEST

stratus-upload-image --repo $APP_REPO \
                     --protocol $PROTOCOL \
                     --curl-option $CURL_OPT \ 
                     --compress $COMPRESSION \
                     --repo-username $USERNAME \
                     --repo-password $PASSWORD \
                     $FORCE_UPLOAD
                     $VM_MANIFEST 

rm -rf $VM_IMAGE $VM_MANIFEST

