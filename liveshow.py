import argparse
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes


def parse_trace(trace_file_name: str) -> pl.DataFrame:
    """
    # parse_trace

    Parse a trace file and return a polars DataFrame.

        Parameters:
            trace_file_name (str): The name of the trace file.

        Returns:
            polars.DataFrame: The parsed trace.

    Format of the trace file:
        (line number as index) gap ddl size prio

        Example:
            ```
            0.1 200 1300 1
            0.1 200 1300 2
    """
    trace = []
    with open(trace_file_name, "r") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            info = re.split(r"\s+", line)
            trace.append(
                {
                    "id": idx,
                    "start": float(info[0]),
                    "ddl": int(info[1]),
                    "size": int(info[2]),
                    "prio": int(info[3]),
                }
            )
    trace = pl.from_dicts(trace)
    trace["start"] = trace["start"].cumsum()
    return trace


def parse_result(result_file_name: str) -> pl.DataFrame:
    """
    # parse_result

    Parse a result file and return a polars DataFrame.

        Parameters:
            result_file_name (str): The name of the result file.

        Returns:
            polars.DataFrame: The parsed result.

    Format of the result file:
        CSV file with following columns:
        - block_id
        - bct
        - size
        - priority
        - deadline
        - duration
    """
    result = pl.read_csv(result_file_name)
    result["block_id"] = result["block_id"].apply(lambda x: (x >> 2) - 1)
    return result


class UpdateData:
    def __init__(
        self, ax: Axes, trace_file_name: str, result_file_name: str, title: str
    ):
        self.trace = parse_trace(trace_file_name)
        self.result_file_name = result_file_name
        self.ax = ax
        self.lines = []
        for i in range(2):
            self.lines.append(self.ax.plot([], [], label=f"Prio {i}")[0])

        # plot parameters
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1.05)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Average In-time Ratio")
        self.ax.set_title(title)
        self.ax.legend()

    def __call__(self, frame):
        x, y = self.calculate()
        self.lines[0].set_data(x, y[1])
        self.lines[1].set_data(x, y[2])
        xlim = max(np.max(x) * 1.1, 1)
        self.ax.set_xlim(0, xlim)
        return self.lines

    def calculate(self):
        # 一个简单粗暴的版本，没有增量更新
        # 其实可以做，但是直接复制比较无脑
        result = parse_result(self.result_file_name)
        result = result.join(self.trace, left_on="block_id", right_on="id", how="outer")
        result = result.filter(pl.col("duration") != None).select(
            [
                "block_id",
                (pl.col("bct") / 1000 < pl.col("ddl")).alias("intime"),
                "prio",
                "ddl",
                (pl.col("ddl") / 1000 + pl.col("start")).alias("timestamp"),
            ]
        )
        x = result["timestamp"].to_numpy()
        y = np.zeros((3, len(x)))
        y_count = np.zeros(3)
        y_intime = np.zeros(3)
        for i in range(len(x)):
            y_count[result["prio"][i]] += 1
            if result["intime"][i]:
                y_intime[result["prio"][i]] += 1
            for j in range(3):
                y[j][i] = y_intime[j] / y_count[j] if y_count[j] > 0 else 1

        return x, y


parser = argparse.ArgumentParser(description="Live Show DTP trace transport")
parser.add_argument("-t", "--trace", type=str, help="trace file", default="trace.txt")
parser.add_argument(
    "-r", "--result", type=str, help="result file", default="result.csv"
)
parser.add_argument("--title", type=str, help="title", default="Live Show")

if __name__ == "__main__":
    args = parser.parse_args()

    fig, ax = plt.subplots()
    update_data = UpdateData(ax, args.trace, args.result, args.title)
    anim = FuncAnimation(fig, update_data, interval=500)
    plt.show()
