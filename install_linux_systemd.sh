INSTALL_DIR=/opt/ipfs_monitor


# get the path of directory this script is currently located in
script_dir="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

PYTHON_DIR=$INSTALL_DIR/PythonVenv

sudo mkdir -p $INSTALL_DIR
sudo chown $USER:$USER $INSTALL_DIR

virtualenv $PYTHON_DIR
source $PYTHON_DIR/bin/activate

pip install -r $script_dir/requirements.txt


cp $script_dir/* $INSTALL_DIR/

echo "[Unit]
Description=IPFS network effects monitor

[Service]
User=$USER
ExecStart=/usr/bin/bash -c 'source $PYTHON_DIR/bin/activate && python3 $INSTALL_DIR'
Restart=always

[Install]
WantedBy=multi-user.target
" | sudo tee /etc/systemd/system/ipfs-monitor.service

sudo systemctl daemon-reload
sudo systemctl enable ipfs-monitor
sudo systemctl restart ipfs-monitor