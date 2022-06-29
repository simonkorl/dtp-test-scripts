import argparse
import os
import re

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP"]


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
    try:
        result = pl.read_csv(result_file_name)
        result["block_id"] = result["block_id"].apply(lambda x: (x >> 2) - 1)
        return result
    except:
        return pl.DataFrame(
            None, ["block_id", "bct", "size", "priority", "deadline", "duration"]
        )


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
        self.table = self.ax.table(
            colLabels=("整体", "高优先", "低优先"),
            rowLabels=["平均块完成时间"],
            cellText=[["NA", "NA", "NA"]],
            bbox=[0.1, -0.4, 0.9, 0.2],
        )

        # plot parameters
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1.05)
        self.ax.set_xlabel("时间 (s)")
        self.ax.set_ylabel("及时到达率")
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
        if result.is_empty():
            self.table[1, 0].get_text().set_text("NA")
            self.table[1, 1].get_text().set_text("NA")
            self.table[1, 2].get_text().set_text("NA")
            return np.array([0]), np.array([[], [], []])

        result = result.join(self.trace, left_on="block_id", right_on="id", how="outer")

        agg = result.select(
            [
                pl.col("bct").mean().alias("avg"),
                pl.col("bct").filter(pl.col("prio") == 1).mean().alias("high"),
                pl.col("bct").filter(pl.col("prio") == 2).mean().alias("low"),
            ]
        )

        self.table[1, 0].get_text().set_text("{:.2f}ms".format(agg["avg"][0]))
        self.table[1, 1].get_text().set_text("{:.2f}ms".format(agg["high"][0]))
        self.table[1, 2].get_text().set_text("{:.2f}ms".format(agg["low"][0]))

        result = result.filter(pl.col("duration") != None).select(
            [
                "block_id",
                (pl.col("bct") < pl.col("ddl")).alias("intime"),
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
    plt.subplots_adjust(bottom=0.3)
    update_data = UpdateData(ax, args.trace, args.result, args.title)
    anim = FuncAnimation(fig, update_data, interval=500)
    plt.show()
