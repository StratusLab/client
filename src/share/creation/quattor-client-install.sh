#!/bin/bash

QUATTORSRV=quattorsrv.lal.in2p3.fr
REPOSITORY=http://${QUATTORSRV}/packages/quattor/sl
REPOSITORY_NCM=http://${QUATTORSRV}/packages/ncm-components
CDBSERVER=${QUATTORSRV}
HOSTNAME=`hostname`

/bin/mkdir -p /tmp/quattor

PERL_RPMS="$REPOSITORY/perl-LC-1.1.2-1.noarch.rpm $REPOSITORY/perl-AppConfig-caf-1.8.2-1.noarch.rpm $REPOSITORY/perl-CAF-1.8.2-1.noarch.rpm"

QUATTOR_RPMS="$REPOSITORY/ccm-2.2.8-1.noarch.rpm $REPOSITORY/ncm-template-1.0.17-1.noarch.rpm $REPOSITORY/ncm-ncd-1.2.26-1.noarch.rpm $REPOSITORY/ncm-query-1.1.0-1.noarch.rpm $REPOSITORY/rpmt-py-1.0.2-1.noarch.rpm $REPOSITORY/spma-1.11.2-1.noarch.rpm $REPOSITORY_NCM/ncm-spma-1.6.0-3.noarch.rpm $REPOSITORY/cdp-listend-1.0.17-1.noarch.rpm $REPOSITORY/ncm-cdispd-1.1.11-1.noarch.rpm"

for r in $PERL_RPMS
do
/usr/bin/curl $r -o /tmp/quattor/`basename $r`
done

for r in $QUATTOR_RPMS
do
/usr/bin/curl $r -o /tmp/quattor/`basename $r`
done

/bin/rpm --force -Uvh /tmp/quattor/*.rpm

rm -rf /tmp/quattor
