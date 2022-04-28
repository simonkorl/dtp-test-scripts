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


def generate_random(random_config, size):
    rng = np.random.default_rng(random_config["seed"])
    match random_config["distribution"]:
        case "integers":
            return rng.integers(low=0, high=random_config["max"], size=size)
        case "choice":
            return rng.choice(
                np.array(random_config["choices"]),
                p=np.array(random_config["probability"]),
                size=size,
            )
        case "uniform":
            return rng.uniform(low=0, high=random_config["max"], size=size)
        case "normal":
            return rng.normal(loc=0, scale=random_config["max"], size=size)
        case "lognormal":
            return rng.lognormal(mean=0, sigma=random_config["max"], size=size)
        case "beta":
            return rng.beta(a=random_config["a"], b=random_config["b"], size=size)
        case "exponential":
            return rng.exponential(scale=random_config["max"], size=size)
        case "pareto":
            return rng.pareto(a=random_config["a"], size=size)
        case "poisson":
            return rng.poisson(lam=random_config["max"], size=size)
        case "binomial":
            return rng.binomial(n=random_config["max"], p=random_config["p"], size=size)
        case "geometric":
            return rng.geometric(p=random_config["p"], size=size)
        case "negative_binomial":
            return rng.negative_binomial(
                n=random_config["max"], p=random_config["p"], size=size
            )


def generate_trace(config):
    # block_size = min(int(config["block_size"]), MAX_BLOCK_SIZE)
    # if block_size <= 0:
    #     block_size = 1350
    block_num = int(config["block_num"])
    # block_gap = 0.001
    # if config.get("block_gap"):
    #     block_gap = float(config["block_gap"])

    block_size = None
    block_gap = None
    block_prio = None
    block_ddl = None

    match config["block_size"]:
        case {"type": "random", "random": r}:
            block_size = generate_random(r, block_num)
        case {"type": "seq", "seq": s}:
            block_size = [s[i % len(s)] for i in range(block_num)]
        case _:
            block_size = np.full(block_num, int(config["block_size"]))

    match config["block_gap"]:
        case {"type": "random", "random": r}:
            block_gap = generate_random(r, block_num)
        case {"type": "seq", "seq": s}:
            block_gap = [s[i % len(s)] for i in range(block_num)]
        case _:
            block_gap = np.full(block_num, float(config["block_gap"]))

    match config["block_prio"]:
        case {"type": "random", "random": r}:
            block_prio = generate_random(r, block_num)
        case {"type": "seq", "seq": s}:
            block_prio = [s[i % len(s)] for i in range(block_num)]
        case _:
            block_prio = np.full(block_num, int(config["block_prio"]))

    match config["block_ddl"]:
        case {"type": "random", "random": r}:
            block_ddl = generate_random(r, block_num)
        case {"type": "seq", "seq": s}:
            block_ddl = [s[i % len(s)] for i in range(block_num)]
        case _:
            block_ddl = np.full(block_num, int(config["block_ddl"]))

    with open(config["trace_file_name"], "w") as f:
        for i in range(block_num):
            block_size_i = block_size[i] if block_size is not None else 1350
            block_gap_i = block_gap[i] if block_gap is not None else 0.001
            block_prio_i = block_prio[i] if block_prio is not None else 0
            block_ddl_i = block_ddl[i] if block_ddl is not None else 200
            f.write(f"{block_gap_i} {block_ddl_i} {block_size_i} {block_prio_i}\n")


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
