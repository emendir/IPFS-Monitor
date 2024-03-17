# IPFS-Monitor

A system for monitoring and limiting IPFS' effect on LAN performance.

This project consists of a python script that monitors network latency with pings and limits the running IPFS node's ability to connect to new peers when the latency surpasses a specified threshold, to avoid the IPFS node from seriously harming the network's internet connectivity.

## Background

IPFS, the InterPlanetary FileSystem, is a great piece of infrastructure for peer-to-peer communications.
In my experience, the main disadvantage it has is that it causes some home routers to overload or crash in different ways.
This issue has so far been tracked in the following Github issue pages:

- https://github.com/ipfs/kubo/issues/3311
- https://github.com/ipfs/kubo/issues/3320
- https://github.com/ipfs/kubo/issues/9998

In my experience, the problem seems to correlate with the number of IPFS peers the concerned node is connected to.
The only effective way I have found so far for limited the number of nodes a peer is connected to is to disable the creation of new IPv4 connections by running the following command:

```sh
ipfs swarm filters add /ip4/0.0.0.0/ipcidr/0
```

Since keeping this configuration active seriously reduces IPFS connectivity, I created this project to automate its activation when the network performance shows signs of overloading, and deactivating it when the performance has reached its baseline again.
Network performance is measured in latency via the average ping times to `/ip4/8.8.8.8`.

I encourage you to adapt this script for other network metrics and IPFS limitation measures you find useful and share your findings to help the community solve this issue which IPFS has.

## Function

This script performs the following loop:

- gather network metrics
- decide whether to apply or remove limitations on IPFS
- log timestamp, network metrics, number of IPFS peers and state of IPFS limitations to a CSV file

### Configuration

Below are the current configurations for the gathered network metrics, the decision logic for applying or removing limitations on IPFS, and what those limitations entail.
I encourage you to adapt this script for other network metrics and IPFS limitation measures you find useful and share your findings to help the community solve this issue which IPFS has.

#### Used Network Metrics

- run a certain number of pings (`PING_SAMPLE_COUNT` times) and calculate their average
  -> however, if a ping times out (after `PING_COMMAND_TIMEOUT_S` seconds), abort the ping sampling immediately

#### Application/Removal of Limitations

- if a ping timed out, apply limitations
- if the average latency was greater than `PING_LIMIT_THRESHOLD_MS` milliseconds, apply limitations
- if the average latency was less than `PING_UNLIMIT_THRESHOLD_MS` milliseconds, remove limitations

#### Limitations

- a swarm filter of `/ip4/0.0.0.0/ipcidr/0`, effectively disabling the creation of new IPv4 connections

## Running from Source

Download this project, install the prerequisites listed in `requirements.txt` and run the folder with Python.

```sh
git clone https://github.com/emendir/IPFS-Monitor
pip install -r IPFS-Monitor/requirements.txt --break-system-packages
python3 IPFS-Monitor
```

## Installation

I've written an installer for Linux systems that use Systemd.
Read it first to make sure you're happy with what it does, e.g. using `pip install --break-system-packages`.

```sh
git clone https://github.com/emendir/IPFS-Monitor
./IPFS-Monitor/install_linux_systemd.sh
```

Logs are written to `/opt/ipfs_monitor/IPFS_Ping_Monitor.csv`