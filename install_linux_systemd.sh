INSTALL_DIR=/opt/ipfs_monitor


# get the path of directory this script is currently located in
script_dir="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

pip install -r $script_dir/requirements.txt --break-system-packages

sudo mkdir -p $INSTALL_DIR
sudo chown $USER:$USER $INSTALL_DIR

cp $script_dir/* $INSTALL_DIR/

echo "[Unit]
Description=IPFS network effects monitor

[Service]
User=$USER
ExecStart=/bin/python3 $INSTALL_DIR

[Install]
WantedBy=multi-user.target
" | sudo tee /etc/systemd/system/ipfs-monitor.service

sudo systemctl daemon-reload
sudo systemctl enable ipfs-monitor
sudo systemctl restart ipfs-monitor