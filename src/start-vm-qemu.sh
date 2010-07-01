#!/bin/bash

GUEST_PORT=2222
HOST_PORT=22
STRATUSLAB_KEY="$HOME/.ssh/stratuslab-stoke.key"
SSH_OPTIONS="-p $GUEST_PORT -i $STRATUSLAB_KEY"
SCP_OPTIONS="-P $GUEST_PORT -i $STRATUSLAB_KEY -q"
INSTALL_SCRIPT="$(dirname $0)/stratuslab.sh"
REMOTE_ENDPOINT="root@localhost"
REMOTE_LOG_FILE="/tmp/stratuslab-install.log"
[ "x$LOCAL_LOG_FILE" = "x" ] && LOCAL_LOG_FILE="/tmp/stratuslab-install-$(date +%Y-%m-%d-%H-%M).log"
REMOTE_DETAILS_FILE="/tmp/stratuslab-install-details.log"
[ "x$LOCAL_DETAILS_FILE" = "x" ] && LOCAL_DETAILS_FILE="/tmp/stratuslab-details-install-$(date +%Y-%m-%d-%H-%M).log"
ARCHIVE_EXTENSION=".tar.gz"
[ "x$STRATUSLAB_STOKE" = "x" ] && STRATUSLAB_STOKE="$HOME/Documents/ubuntu-server-stratuslab-base"

log_message() {
    echo "$(date): $*" 
}

log_message "Extracting stoke image..."
cd $(dirname $STRATUSLAB_STOKE)
tar -xzf $STRATUSLAB_STOKE$ARCHIVE_EXTENSION
cd - >/dev/null

log_message "Starting VM..."
qemu $STRATUSLAB_STOKE -nographic -redir tcp:$GUEST_PORT::$HOST_PORT &>/dev/null &

log_message "Waiting VM to boot..."
[ "x$BOOT_SLEEP_TIME" = "x" ] && BOOT_SLEEP_TIME=15
sleep $BOOT_SLEEP_TIME

log_message "Copy install script..."
scp $SCP_OPTIONS $INSTALL_SCRIPT $REMOTE_ENDPOINT:

log_message "Installing ONE & dependencies..."
ssh $SSH_OPTIONS $REMOTE_ENDPOINT "bash $(basename $INSTALL_SCRIPT) 2>$REMOTE_DETAILS_FILE | tee $REMOTE_LOG_FILE"
INSTALL_EXIT_CODE=$?

log_message "Retrieve install logs..."
scp $SCP_OPTIONS $REMOTE_ENDPOINT:$REMOTE_LOG_FILE $LOCAL_LOG_FILE
scp $SCP_OPTIONS $REMOTE_ENDPOINT:$REMOTE_DETAILS_FILE $LOCAL_DETAILS_FILE

log_message "Shutting down VM..."
ssh $SSH_OPTIONS $REMOTE_ENDPOINT "shutdown -h now"

log_message "Install finished with exit code $INSTALL_EXIT_CODE"
exit $INSTALL_EXIT_CODE

