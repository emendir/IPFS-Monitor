from time import sleep
import toml
import ipaddress
from loguru import logger
import time
import ipfs_api
import subprocess
import re
import os
import sys
# how many seconds to wait before
# giving up on a ping operation and applying IPFS limitations
PING_COMMAND_TIMEOUT_S = 2

# upper and lower thresholds for applying/removing IPFS limitations
PING_LIMIT_THRESHOLD_MS = 40
PING_UNLIMIT_THRESHOLD_MS = 30
MAX_PEERS_COUNT = 800

PING_IP_ADDRESS = '8.8.8.8'  # IP address to use for ping tests
# number of pings to average when compiling latency metrics
PING_SAMPLE_COUNT = 10
# path of the file to which to write logs
LOG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'IPFS_Ping_Monitor.csv'
)


# Default whitelist and blacklist
DEFAULT_WHITELIST = [
    "127.0.0.0/8",
    "192.168.0.0/16",
    "172.16.0.0/12",
    "10.0.0.0/8",
]
DEFAULT_BLACKLIST = []

# Load configuration from a TOML file


def load_config():
    try:
        config = toml.load(os.path.join(
            os.path.dirname(__file__), "config.toml")
        )
        whitelist = config.get("whitelist", DEFAULT_WHITELIST)
        blacklist = config.get("blacklist", DEFAULT_BLACKLIST)
        logger.warning("Loaded blacklist and whitelist from config.")
    except Exception as e:
        logger.warning(f"Failed to load config: {e}, using defaults.")
        whitelist = DEFAULT_WHITELIST
        blacklist = DEFAULT_BLACKLIST
    return whitelist, blacklist


whitelist, blacklist = load_config()


def get_complement_cidrs(allowed_cidrs, blocked_cidrs):
    """Calculate CIDR blocks that exclude `allowed_cidrs` and include `blocked_cidrs`."""
    full_range = ipaddress.IPv4Network("0.0.0.0/0")
    allowed = [ipaddress.IPv4Network(cidr) for cidr in allowed_cidrs]
    blocked = [ipaddress.IPv4Network(cidr) for cidr in blocked_cidrs]

    excluded_ranges = set(allowed) - set(blocked)

    result_ranges = [full_range]
    for exclude in sorted(excluded_ranges, key=lambda net: net.prefixlen, reverse=True):
        temp_ranges = []
        for rng in result_ranges:
            # Ensure the excluded range is within the current range
            if exclude.subnet_of(rng):
                temp_ranges.extend(rng.address_exclude(exclude))
            else:
                temp_ranges.append(rng)
        result_ranges = temp_ranges

    return result_ranges


def apply_strict_filters():
    """Apply IPFS filters to block all IPs except the whitelisted ones."""
    try:
        logger.info("Applying strict filters")
        remove_all_filters()

        filters_to_apply = get_complement_cidrs(whitelist, blacklist)
        multi_addr_filters = [
            f"/ip4/{cidr.network_address}/ipcidr/{cidr.prefixlen}"
            for cidr in filters_to_apply
        ]
        for multi_addr in multi_addr_filters:
            logger.debug(f"Adding filter: {multi_addr}")
            ipfs_api.add_swarm_filter(multi_addr)
    except ipfs_api.ipfshttpclient.exceptions.ErrorResponse:
        # this error always gets thrown, isn't a problem
        pass
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {e}")


def remove_all_filters():
    """Remove all currently applied IPFS filters."""
    try:
        logger.info("Removing all filters")
        filters = ipfs_api.get_swarm_filters()
        for filter_entry in filters:
            logger.debug(f"Removing filter: {filter_entry}")
            ipfs_api.rm_swarm_filter(filter_entry)
    except ipfs_api.ipfshttpclient.exceptions.ErrorResponse:
        # this error always gets thrown, isn't a problem
        pass
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {e}")


def remove_strict_filters():
    """Remove all filters and apply blacklist as new filters."""
    try:
        logger.info("Removing strict filters and applying blacklist")
        remove_all_filters()
        for cidr in blacklist:
            multi_addr = f"/ip4/{cidr.network_address}/ipcidr/{cidr.prefixlen}"
            logger.info(f"Blacklisting: {multi_addr}")
            ipfs_api.add_swarm_filter(multi_addr)
    except ipfs_api.ipfshttpclient.exceptions.ErrorResponse:
        # this error always gets thrown, isn't a problem
        pass
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {e}")


def are_strict_filters_applied():
    """Check if only the correct filters are applied."""
    try:

        filters = ipfs_api.get_swarm_filters()

        expected_filters = {
            f"/ip4/{cidr.network_address}/ipcidr/{cidr.prefixlen}"
            for cidr in get_complement_cidrs(whitelist, blacklist)
        }
        result = filters == expected_filters
        logger.info(f"Strict filters applied: {result}")
        return result
    except ipfs_api.ipfshttpclient.exceptions.ConnectionError as e:
        logger.error(f"ConnectionError: {e}")
        return False


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
    limitation = are_strict_filters_applied()

    total_time = 0
    lost_pings = False
    for _ in range(PING_SAMPLE_COUNT):
        latency = get_ping_latency(PING_IP_ADDRESS, PING_COMMAND_TIMEOUT_S)
        if not latency:
            lost_pings = True
            break
        total_time += latency
        time.sleep(1)  # 1-second interval between pings
    if peers_count > MAX_PEERS_COUNT and not limitation:
        apply_strict_filters()
    average_time = int(total_time / PING_SAMPLE_COUNT)
    if limitation:
        if not lost_pings and average_time < PING_UNLIMIT_THRESHOLD_MS and peers_count < MAX_PEERS_COUNT:
            remove_strict_filters()
    else:
        if lost_pings or average_time > PING_LIMIT_THRESHOLD_MS:
            apply_strict_filters()
    logger.info(f"{average_time},{peers_count},{int(limitation)}")


def get_num_ipfs_peers():
    """Get the number of peers this IPFS node is connected to."""
    try:
        return len(list(dict(ipfs_api.http_client.swarm.peers())['Peers']))
    except Exception:
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
    remove_strict_filters()
    while (True):
        try:
            check_pings()
        except ipfs_api.ipfshttpclient.exceptions.ConnectionError as e:
            logger.error(f"ConnectionError: {e}")
        sleep(1)


if __name__ == '__main__':
    run_monitor()
