
import os
import platform
import json
import sys
import time
import re
from tqdm import tqdm
import pandas as pd

CLIENT_LOG_PATTERN = re.compile(
    r'connection closed, recv=(-?\d+) sent=(-?\d+) lost=(-?\d+) rtt=(?:(?:(\d|.+)ms)|(?:(-1))) cwnd=(-?\d+), total_bytes=(-?\d+), complete_bytes=(-?\d+), good_bytes=(-?\d+), total_time=(-?\d+)')
CLIENT_STAT_INDEXES = ["c_recv", "c_sent", "c_lost",
                       "c_rtt(ms)", "c_cwnd", "c_total_bytes", "c_complete_bytes", "c_good_bytes", "c_total_time(us)", "qoe", "retry_times"]
CLIENT_BLOCKS_INDEXES = ["BlockID", "bct", "BlockSize", "Priority", "Deadline"]


def parse_client_log(dir_path):
    '''
    Parse client.log and get two dicts of information.

    `client_blocks_dict` stores information in client.log about block's stream_id, bct, deadline and priority
    `client_stat_dict` stores statistics offered in client.log. Some important information is like goodbytes and total running time(total time)
    '''
    # collect client blocks information
    client_blocks_dict = {}
    for index in CLIENT_BLOCKS_INDEXES:
        client_blocks_dict[index] = []
    # collect client stats
    client_stat_dict = {}
    for index in CLIENT_STAT_INDEXES:
        client_stat_dict[index] = []

    with open(os.path.join(dir_path, "client.log")) as client:
        client_lines = client.readlines()

        for line in client_lines[4:-1]:
            if len(line) > 1:
                client_line_list = line.split()
                if len(client_line_list) != len(CLIENT_BLOCKS_INDEXES):
                    print(
                        "A client block log line has error format in : %s. This happens sometime." % dir_path)
                    continue
                for i in range(len(client_line_list)):
                    client_blocks_dict[CLIENT_BLOCKS_INDEXES[i]].append(
                        client_line_list[i])

        # try to parse the last line of client log
        try:
            match = CLIENT_LOG_PATTERN.match(client_lines[-1])
            if match == None:
                raise ValueError(
                    "client re match returns None in : %s" % dir_path, client_lines[-1])

            client_stat_dict["c_recv"].append(float(match.group(1)))
            client_stat_dict["c_sent"].append(float(match.group(2)))
            client_stat_dict["c_lost"].append(float(match.group(3)))

            if match.group(4) is None:
                client_stat_dict["c_rtt(ms)"].append(float(-1))
            else:
                client_stat_dict["c_rtt(ms)"].append(float(match.group(4)))

            client_stat_dict["c_cwnd"].append(float(match.group(6)))
            client_stat_dict["c_total_bytes"].append(float(match.group(7)))
            client_stat_dict["c_complete_bytes"].append(float(match.group(8)))
            client_stat_dict["c_good_bytes"].append(float(9))
            client_stat_dict["c_total_time(us)"].append(float(match.group(10)))

            # invalid stat
            client_stat_dict["qoe"].append(-1)
            client_stat_dict["retry_times"].append(-1)

            return client_blocks_dict, client_stat_dict
        except:
            return None, None


if __name__ == "__main__":
    argv = sys.argv
    dir_path = "../aitrans-server"
    if (len(argv) >= 2):
        dir_path = argv[1]
    client_blocks_dict, client_stat_dict = parse_client_log(
        dir_path)
    blocks = pd.DataFrame(client_blocks_dict)
    stats = pd.DataFrame(client_stat_dict)
    blocks.to_csv("blocks.csv", index=False)
    stats.to_csv("stats.csv", index=False)
