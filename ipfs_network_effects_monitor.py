from scapy.all import *
from loguru import logger
import time
from datetime import datetime
import ipfs_api
import subprocess
import re

# how many seconds to wait before
# giving up on a ping operation and applying IPFS limitations
PING_COMMAND_TIMEOUT_S = 2

# upper and lower thresholds for applying/removing IPFS limitations
PING_LIMIT_THRESHOLD_MS = 40
PING_UNLIMIT_THRESHOLD_MS = 30

PING_IP_ADDRESS = '8.8.8.8'  # IP address to use for ping tests
# number of pings to average when compiling latency metrics
PING_SAMPLE_COUNT = 10
# path of the file to which to write logs
LOG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'IPFS_Ping_Monitor.csv'
)


def limit_ipfs():
    """Apply limitations to IPFS to reduce network harm."""
    try:
        ipfs_api.http_client.swarm.filters.add('/ip4/0.0.0.0/ipcidr/0')
    except ipfs_api.ipfshttpclient.exceptions.ErrorResponse:
        # this error always gets thrown, isn't a problem
        pass
        pass
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError:
        pass


def unlimit_ipfs():
    """Remove limitations that reduce network harm."""
    try:
        ipfs_api.http_client.swarm.filters.rm('/ip4/0.0.0.0/ipcidr/0')
    except ipfs_api.ipfshttpclient.exceptions.ErrorResponse:
        # this error always gets thrown, isn't a problem
        pass
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError:
        pass


def are_limitations_applied():
    """Check if limitations that reduce network harm are active."""
    try:
        filters = dict(ipfs_api.http_client.swarm.filters.list())['Strings']
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError:
        return False
    if not filters:
        filters = []
    return '/ip4/0.0.0.0/ipcidr/0' in filters


def get_ping_latency(PING_IP_ADDRESS, timeout):
    """"""
    ping_process = subprocess.Popen(
        ['ping', '-c', '1', '-W', str(timeout), PING_IP_ADDRESS], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    start_time = time.time()
    output, _ = ping_process.communicate()
    end_time = time.time()

    if ping_process.returncode == 0:
        match = re.search(r'time=([\d.]+) ms', output.decode('utf-8'))
        if match:
            return float(match.group(1))


def check_pings():
    """
    Gather network metrics, limit or unlimit IPFS accordingly, log results."""
    peers_count = get_num_ipfs_peers()
    limitation = are_limitations_applied()

    total_time = 0
    lost_pings = False
    for _ in range(PING_SAMPLE_COUNT):
        latency = get_ping_latency(PING_IP_ADDRESS, PING_COMMAND_TIMEOUT_S)
        if not latency:
            lost_pings = True
            break
        total_time += latency
        time.sleep(1)  # 1-second interval between pings

    if lost_pings:
        average_time = -1
        limit_ipfs()
        time.sleep(1)
    else:
        average_time = int(total_time / PING_SAMPLE_COUNT)

        if average_time > PING_LIMIT_THRESHOLD_MS:
            limit_ipfs()
        elif average_time < PING_UNLIMIT_THRESHOLD_MS:
            unlimit_ipfs()
    logger.info(f"{average_time},{peers_count},{int(limitation)}")


def get_num_ipfs_peers():
    """Get the number of peers this IPFS node is connected to."""
    try:
        return len(list(dict(ipfs_api.http_client.swarm.peers())['Peers']))
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError:
        return 0


# Set up log rotation with retention
logger.remove(0)    # remove default logger
# add custom logger for printing to console
logger.add(sys.stdout, format="<level>{message}</level>")
# add logger for writing to log file
logger.add(
    LOG_FILE_PATH,
    format="{time:DD-MMM-YYYY HH:mm:ss},{message}",
    rotation="1 MB", retention="5 days"
)


def run_monitor():
    unlimit_ipfs()
    while (True):
        check_pings()


if __name__ == '__main__':
    run_monitor()
