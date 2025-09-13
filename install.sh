#!/bin/bash
## Install this project's source code on this or a remote machine.
## This script performs the following steps:
## 1. Copy project source code to installation directory.
##   - For remote installation, copy this project and rerun this script there
## 2. If $INSTALL, 
##   a) run install_prereqs.sh
##   b) run setup.sh
##   c) install all systemd unit files in $SYSTEMD_UNITS_DIR


""":"
SSH_ADDRESS=$1 # leave blank to install locally (if DEF_SSH_ADDRESS is also blank), or set to "-" to force installing locally
INSTALL_DIR=$2 # absolute path to copy project to
INSTALL=$3 # ('true' | 'false') whether or not to run install_prereqs.sh & setup.sh and install systemd-units after copying files

# the absolute paths of this script and it's directory
SCRIPT_PATH=$(realpath -s "$0") # DON'T EDIT - must be absolute paths
SCRIPT_DIR=$(dirname "$SCRIPT_PATH") # DON'T EDIT - must be absolute paths

PROJ_NAME=$(basename $SCRIPT_DIR)
PROJ_DIR=$SCRIPT_DIR # must be an absolute path, with this script in its tree
RSYNC_IGNORE=$PROJ_DIR/.gitignore
SYSTEMD_UNITS_DIR="systemd_units" # path relative to PROJ_DIR which contains systemd unit files to be installed

# absolute path to copy this projects files to for installation
DEF_INSTALL_DIR=/opt/$PROJ_NAME
# whether or not to run the installer
# on the remote system after copying over the files
DEF_INSTALL=1 
# leave blank to install locally if user doesn't specify SSH_ADDRESS
DEF_SSH_ADDRESS=""




# if no parameter was passed
if [ -z "$SSH_ADDRESS" ]; then
  SSH_ADDRESS=$DEF_SSH_ADDRESS
fi
# for forcing local installation
if [ "$SSH_ADDRESS" = "-" ]; then
  SSH_ADDRESS=""
fi

# if no parameter was passed
if [ -z "$INSTALL_DIR" ]; then
  INSTALL_DIR=$DEF_INSTALL_DIR
fi
# if no parameter was passed
if [ -z "$INSTALL" ]; then
  INSTALL=$DEF_INSTALL
fi


BLACK='\033[0;30m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
NC='\033[0m' # no colour

notify () {
    local message="$1"
    local color="${2:-$NC}" # Default color is 'no colour' if no argument is provided

    echo ""
    echo -e "${color}----------------------------------------"
    echo -e "${color}${message}"
    echo -e "${color}----------------------------------------${NC}"
    echo ""
}

# get path of this script relative to PROJ_DIR
# after asserting SCRIPT_PATH is inside PROJ_DIR
case "$SCRIPT_PATH" in
  "$PROJ_DIR"/*)
    # Strip the prefix and leading slash
    REL_SCRIPT_PATH=${SCRIPT_PATH#"$PROJ_DIR"/}
    ;;
  *)
    echo -e "${RED}Error: SCRIPT_PATH is not inside PROJ_DIR (or PROJ_DIR is not an absolute path)${NC}" >&2
    exit 1
    ;;
esac

if ! [ -e $RSYNC_IGNORE ];then
  touch $RSYNC_IGNORE
fi

# install on remote host if required
if ! [ -z "$SSH_ADDRESS" ];then
  username=$(echo $SSH_ADDRESS | awk -F "@" '{print $1}')
  notify "Creating remote directory..." $MAGENTA
  # create install dir if not existant
  ssh $SSH_ADDRESS -t "if ! [ -d $INSTALL_DIR ]; then sudo mkdir -p $INSTALL_DIR;  sudo chown $username:$username $INSTALL_DIR; fi;"

  notify "Copying files to remote directory..." $MAGENTA
  # copy project files to install dir on remote host
  rsync -XAva --delete "$PROJ_DIR/" "${SSH_ADDRESS}:${INSTALL_DIR}/" --exclude-from=$RSYNC_IGNORE

  if [ $INSTALL ];then
    echo ""
    notify "Re-Running this installer on remote machine." $BLUE
    echo ""
    # run this script on remote host to install this project there
    ssh $SSH_ADDRESS -t "$INSTALL_DIR/$REL_SCRIPT_PATH '-' $INSTALL_DIR $INSTALL"
  fi
    
  exit 0 # exit this script to avoid installing locally
fi

# Copy project to installation path locally
notify "Installing $PROJ_NAME
Installing to:  $INSTALL_DIR
Project source: $PROJ_DIR" $MAGENTA

cd $SCRIPT_DIR
set -e # Exit if any command fails



if ! [ -e $INSTALL_DIR ];then
  sudo mkdir -p $INSTALL_DIR
fi

# copy project dir to install dir if not already running from installation
if ! [[ $INSTALL_DIR -ef $PROJ_DIR ]]; then
  notify "Copying files..." $MAGENTA
  sudo rsync -XAva --delete $PROJ_DIR/ $INSTALL_DIR/ --exclude-from=$RSYNC_IGNORE
fi



if [ "$INSTALL" -eq 1 ]; then
  
  # install project locally
  notify "Installing prerequisites..." $MAGENTA
  $INSTALL_DIR/install_prereqs.sh
  notify "Running setup script..." $MAGENTA
  $INSTALL_DIR/setup.sh

  notify "Installing Systemd services and timers..." $MAGENTA
  SYSD="$INSTALL_DIR/$SYSTEMD_UNITS_DIR" # get dir containing unit files
  if [ -e $SYSD ];then
    # Loop through systemd unit files
    for unit in "$SYSD"/*.service "$SYSD"/*.timer "$SYSD"/*.socket "$SYSD"/*.target "$SYSD"/*.mount "$SYSD"/*.automount "$SYSD"/*.path "$SYSD"/*.device "$SYSD"/*.swap "$SYSD"/*.slice "$SYSD"/*.scope; do
        # Skip if no matching files
        [ -e "$unit" ] || continue
        echo -e "${MAGENTA}- $(basename "$unit")${NC}"

        # Copy to systemd directory
        sudo cp "$unit" /etc/systemd/system/

        # Reload systemd to recognize new unit
        sudo systemctl daemon-reexec
        sudo systemctl daemon-reload

        # Enable and start the unit, restarting if already existant
        sudo systemctl enable "$(basename "$unit")"
        sudo systemctl restart "$(basename "$unit")"
    done
  else
    echo -e "${YELLOW}Didn't find Systemd unit files, directory doesn't exist:"
    echo -e $SYSD
    echo -e $NC
  fi
fi


notify "Done!" $MAGENTA




























exit 0
"""
import os
import sys

# Python: re-execute the script in Bash
os.execvp('bash', ['bash', __file__] + sys.argv[1:])

#"
