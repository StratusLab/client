#!/bin/bash

ONE_GIT_REPO="git://opennebula.org/one.git"
ONE_BRANCH="one-1.4"

ONE_BUILD="/tmp/one"
ONE_CLONE_NAME="two"

ONE_USER_GROUP="cloud"
ONE_USER_ID="10001"
ONE_USER_NAME="oneadmin"
ONE_PASSWORD="oneadmin"
ONE_HOME="/srv/cloud/one"
ONE_SSH_KEY="$ONE_HOME/.ssh/oneadmin"

log_message() {
    echo "$(date): $*"
    echo "$(date): $*" 1>&2
}

mkdir -p $ONE_BUILD
cd $ONE_BUILD

log_message "Installing dependencies..."
apt-get -y -qq install ruby libsqlite3-dev libxmlrpc-c3-dev\
 libssl-dev scons g++ qemu-kvm git-core 1>&2

log_message "Downloading ONE..."
git clone $ONE_GIT_REPO $ONE_CLONE_NAME -b $ONE_BRANCH 1>&2 

log_message "Building ONE..."
cd $ONE_CLONE_NAME
scons -j2 1>&2

log_message "Creating ONE admin home directory..."
mkdir -p $(dirname $ONE_HOME)

log_message "Creating ONE admin user and group..."
groupadd -g $ONE_USER_ID $ONE_USER_GROUP
useradd -d $ONE_HOME -g $ONE_USER_GROUP -u $ONE_USER_ID $ONE_USER_NAME\
 -s /bin/bash -p $ONE_PASSWORD --create-home

log_message "Installing ONE software..."
su - $ONE_USER_NAME -c "cd $(pwd) && bash install.sh -d $ONE_HOME"

log_message "Configuring ONE admin environment..."
echo "export ONE_LOCATION=$ONE_HOME" >> $ONE_HOME/.bashrc
echo "export ONE_XMLRPC=http://localhost:2633/RPC2" >> $ONE_HOME/.bashrc
echo "export PATH=$ONE_HOME/bin:$PATH" >> $ONE_HOME/.bashrc
su - $ONE_USER_NAME -c "echo '[ -f ~/.bashrc ] && source ~/.bashrc' >> $ONE_HOME/.bash_login"
# Hack to always load bashrc
sed -i 's/\[ -z \"\$PS1\" \] \&\& return/#&/' $ONE_HOME/.bashrc

log_message "Configuring ONE admin credentials..."
su -l $ONE_USER_NAME -c "mkdir -p $ONE_HOME/.one"
su -l $ONE_USER_NAME -c "echo $ONE_USER_NAME:$ONE_PASSWORD > $ONE_HOME/.one/one_auth"

log_message "Configuring ONE admin SSH keys..."
su -l $ONE_USER_NAME -c "ssh-keygen -f $ONE_SSH_KEY -N '' -q"
su -l $ONE_USER_NAME -c "cp -f $ONE_SSH_KEY.pub $ONE_HOME/.ssh/authorized_keys"
su -l $ONE_USER_NAME -c "echo -e 'Host *\n\tStrictHostKeyChecking no' > $ONE_HOME/.ssh/config"

log_message "Starting ONE daemon..."
su -l $ONE_USER_NAME -c "one start 1>&2"

log_message "Adding ONE host..."
su -l $ONE_USER_NAME -c "onehost create localhost im_kvm vmm_kvm tm_nfs"

log_message "Stratuslab install finished"

