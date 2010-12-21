#!/bin/bash
PATH="/usr/bin:/bin:/sbin"

export PATH=$PATH:/sbin
ROUTE=`route -n | awk '{if ($1 == "0.0.0.0") print $2}' `
IP=`ifconfig | grep ${ROUTE%.*} | awk '{print $2}'`
IP=${IP#*:}
IPHOSTNAME=${IP}:`hostname`

# check KVM support.
# first check if the library is returned with the modprobe command.
# if not, set "KVM is not installed".
# if it is returned, then check to see if the file exists.
# if the file exists, grep to find version number. If it does not exist, return "KVM is not installed."

KVMLIBFILE=`modprobe -l kvm --show-depends` 
if [ -z ${KVMLIBFILE} ];
   then
    # kvmlibfile is empty. kvm is not installed
     KVMVERSION="KVM is not installed"
   else
        # kvmlibfile is not empty. check if it exists.
	if [ -e ${KVMLIBFILE} ];
	   then
	     KVMVERSION=`strings ${KVMLIBFILE} | grep -i ^version`
	     #echo "mpika edo"
	    KVMVERSION=${KVMVERSION#*=}
	   else
	     KVMVERSION="KVM is not installed"
	fi
fi 

# now check XEN version
# first, check to find xen in the uname -a
# if you cannot find it, then return "xen is not installed"
# if you find it, then run an xm list and search for domain-0
# if you find domain-0, then return the kernel name as xen version.
# if you cannot find Domain-0, then return "xen is not installed"

XENKERNELNAME=`uname -r | grep xen`

if [ -z ${XENKERNELNAME} ];
  then
   # xen is not installed.
   XENVERSION="XEN is not installed"
  else
   # run an xm list and search for dom-0
   DOMZEROEXISTS=`xm list | grep Domain-0`
   if [ -z "${DOMZEROEXISTS}" ];
     then
     #dom0 is not present, so XEN is not installed
     XENVERSION="XEN is not installed"
     else
     # dom0 is present, so return uname as xenversion
     XENVERSION="${XENKERNELNAME}"
   fi
fi


# -d 86450 expires the metric every day. This means that if the metric is not updated every day, it will disappear.

gmetric -n 'KVM_VERSION' -v "${KVMVERSION}" -d 86450 -t string -S ${IPHOSTNAME} > /dev/null
gmetric -n 'XEN_VERSION' -v "${XENVERSION}" -d 86450 -t string -S ${IPHOSTNAME} > /dev/null

#echo ${KVMVERSION}
#echo ${XENVERSION}


