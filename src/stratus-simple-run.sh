#!/bin/bash

GUEST_PORT=2222
HOST_PORT=22
STRATUSLAB_KEY="$HOME/.ssh/stratuslab-stoke.key"
SSH_OPTIONS="-p $GUEST_PORT -i $STRATUSLAB_KEY"
SCP_OPTIONS="-P $GUEST_PORT -i $STRATUSLAB_KEY -q -r"
ONE_FRONTEND_ENDPOINT="root@localhost"
ONE_NODE_ADDRESSES=( "localhost" )
ONE_FRONTEND_INSTALL_DIR="stratuslab"

log_message() {
    echo "$(date): $*" 
}

exit_on_error() {
    if [ $? -ne 0 ]; then
        LAST_COMMAND="!!"
        echo "Failled executing command: $LAST_COMMAND"       
        exit 1
    fi
}

log_message "Copy install script..."
scp $SCP_OPTIONS src $ONE_FRONTEND_ENDPOINT:$ONE_FRONTEND_INSTALL_DIR
exit_on_error

log_message "Configure stratuslab..."
ssh $SSH_OPTIONS $ONE_FRONTEND_ENDPOINT "python $ONE_FRONTEND_INSTALL_DIR/stratus-config.py"
exit_on_error

log_message "Install stratuslab..."
ssh $SSH_OPTIONS $ONE_FRONTEND_ENDPOINT "python $ONE_FRONTEND_INSTALL_DIR/stratus-install.py"
exit_on_error

for NODE in ${ONE_NODE_ADDRESSES[*]}; do
    log_message "Install stratuslab node $NODE..."
    ssh $SSH_OPTIONS $ONE_FRONTEND_ENDPOINT "python $ONE_FRONTEND_INSTALL_DIR/stratus-install.py -n $NODE"
    exit_on_error
done

