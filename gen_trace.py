import argparse
import json
import os
from typing import List, Dict
import numpy as np

MAX_BLOCK_SIZE = 10000000
MAX_DGRAM_SIZE = 1350


def parse_config(config_file: str):
    with open(config_file, "r") as f:
        return json.load(f)


def generate_trace(config):
    block_size = min(int(config["block_size"]), MAX_BLOCK_SIZE)
    if block_size <= 0:
        block_size = 1350
    block_num = int(config["block_num"])
    block_gap = 0.001
    if config.get("block_gap"):
        block_gap = float(config["block_gap"])

    with open(config["trace_file_name"], "w") as f:
        if type(config["block_prio"]) == int:
            for i in range(block_num):
                f.write(
                    "%f %d %d %d\n"
                    % (
                        block_gap,
                        int(config["block_ddl"]),
                        block_size,
                        int(config["block_prio"]),
                    )
                )
        elif config["block_prio"]["type"] == "seq":
            for i in range(block_num):
                f.write(
                    "%f %d %d %d\n"
                    % (
                        block_gap,
                        int(config["block_ddl"]),
                        block_size,
                        int(
                            config["block_prio"]["seq"][
                                i % len(config["block_prio"]["seq"])
                            ]
                        ),
                    )
                )
        elif config["block_prio"]["type"] == "random":
            rng = np.random.default_rng(config["block_prio"]["random"]["seed"])
            block_prio = []
            if config["block_prio"]["random"]["distribution"] == "integers":
                block_prio = rng.integers(
                    low=0, high=config["block_prio"]["random"]["max"], size=block_num
                )
            elif config["block_prio"]["random"]["distribution"] == "choice":
                block_prio = rng.choice(
                    np.array(config["block_prio"]["random"]["choices"]),
                    p=np.array(config["block_prio"]["random"]["probability"]),
                    size=block_num,
                )
            for i in range(block_num):
                f.write(
                    "%f %d %d %d\n"
                    % (block_gap, int(config["block_ddl"]), block_size, block_prio[i])
                )
        else:
            pass


parser = argparse.ArgumentParser(description="Generate trace for testing")
parser.add_argument(
    "configs",
    metavar="cfg",
    type=str,
    nargs="+",
    help="configs used to generate traces",
)

if __name__ == "__main__":
    args = parser.parse_args()
    for config_file in args.configs:
        for config in parse_config(config_file):
            generate_trace(config)
