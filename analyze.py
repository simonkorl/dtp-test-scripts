import argparse
import csv
import re
import polars as pl
import numpy as np
import matplotlib.pyplot as plt

import utils


def parse_trace(trace_file_name):
    trace = []
    with open(trace_file_name, "r") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            info = re.split(r"\s+", line)
            trace.append(
                {
                    "id": idx,
                    "gap": float(info[0]),
                    "ddl": int(info[1]),
                    "size": int(info[2]),
                    "prio": int(info[3]),
                }
            )
    return pl.from_dicts(trace)


def find_unsend(result_file_name, trace_file_name):
    if trace_file_name is not None:
        block_num = utils.count_newlines(trace_file_name)
        trace = set(range(block_num))

        with open(result_file_name, "r") as f:
            reader = csv.DictReader(f)
            result = [((int(row["block_id"]) - 1) >> 2) - 1 for row in reader]

        return sorted([(x, ((x + 1) << 2) + 1) for x in trace - set(result)])
    else:
        raise Exception("trace_file_name is None")


def total_time(trace_file_name):
    with open(trace_file_name, "r") as f:
        reader = csv.reader(f, delimiter=" ")
        return sum([float(row[0]) for row in reader])


def draw(result_file_name, trace_file_name):
    result = pl.read_csv(result_file_name)
    result["block_id"] = result["block_id"].apply(lambda x: (x >> 2) - 1)
    trace = parse_trace(trace_file_name).rename({"gap": "start"})
    trace["start"] = trace["start"].cumsum()
    result = result.join(trace, left_on="block_id", right_on="id", how="outer")
    result = result.select(
        [
            "block_id",
            (pl.col("bct") < pl.col("deadline")).alias("intime"),
            "prio",
            "ddl",
            (pl.col("ddl") / 1e3 + pl.col("start")).alias("timestamp"),
        ]
    )
    print(result)

    x = result["timestamp"].to_numpy()
    y = np.zeros((8, len(x)))
    y_count = np.zeros(8)
    y_intime = np.zeros(8)
    for i in range(len(x)):
        y_count[result["prio"][i]] += 1
        if result["intime"][i]:
            y_intime[result["prio"][i]] += 1
        for j in range(8):
            y[j][i] = y_intime[j] / y_count[j] if y_count[j] > 0 else 0

    fig, ax = plt.subplots()
    ax.plot(x, y[0], label="prio 0")
    ax.plot(x, y[1], label="prio 1")
    ax.plot(x, y[2], label="prio 2")
    ax.plot(x, y[3], label="prio 3")
    ax.plot(x, y[4], label="prio 4")
    ax.plot(x, y[5], label="prio 5")
    ax.plot(x, y[6], label="prio 6")
    ax.plot(x, y[7], label="prio 7")

    ax.set_xlabel("time (s)")
    ax.set_ylabel("average intime ratio")
    ax.legend()
    plt.savefig("intime_ratio.png")

    result = result.groupby("prio").agg(
        [pl.count(), (pl.col("intime") == True).sum()]
    )
    print(result)


parser = argparse.ArgumentParser(description="Analyze result")
parser.add_argument(
    "command",
    metavar="cmd",
    type=str,
    choices=["find_unsend", "total_time", "draw", "hist"],
)
parser.add_argument(
    "-r",
    "--result_file",
    metavar="result",
    type=str,
    help="result files to analyze",
)
parser.add_argument("-t", "--trace_file", metavar="trace", type=str, help="trace file")

if __name__ == "__main__":
    args = parser.parse_args()

    match args.command:
        case "find_unsend":
            print(find_unsend(args.result_file, args.trace_file))
        case "total_time":
            print(total_time(args.trace_file))
        case "draw":
            draw(args.result_file, args.trace_file)
        case "hist":
            raise Exception("Not implemented")
        case _:
            raise Exception("Unknown command")
