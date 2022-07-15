import argparse
import os
import re
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP"]


re_complete_pattern = r"\[INFO\] quiche: stream (\d+) send complete"
re_cancel_pattern = (
    r"\[INFO\] quiche::scheduler::dtp_scheduler: block (\d+) is canceled, passed (\d+)"
)


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
        (line number as index) gap ddl size prio

        [INFO] quiche::scheduler::dtp_scheduler: block 2241 is canceled, passed 238
        [INFO] quiche: stream 2245 send complete
    """

    def find_info(line: str):
        if m := re.match(re_complete_pattern, line):
            return ((int(m.group(1)) >> 2) - 1, "complete")
        elif m := re.match(re_cancel_pattern, line):
            return ((int(m.group(1)) >> 2) - 1, "cancel")
        else:
            return None

    with open(result_file_name, "r") as f:
        lines = f.readlines()

        result = [info for line in lines if (info := find_info(line)) is not None]

        if len(result) == 0:
            result = None

        return pl.DataFrame(
            result, columns=[("id", pl.Int64), ("status", pl.Utf8)], orient="row"
        )


class UpdateData:
    def __init__(
        self, axs: Axes, trace_file_name: str, result_file_name: str, title: str
    ):
        self.trace = parse_trace(trace_file_name)
        self.result_file_name = result_file_name
        self.title = title
        self.axs = axs

    def __call__(self, frame):
        agg = self.calculate()

        self.axs[0].clear()
        self.axs[0].axis("equal")
        self.axs[0].set_title(self.title + " 高优先级")
        self.axs[0].pie(
            [agg["high complete"][0], agg["high cancel"][0], agg["high wait"][0]],
            labels=["已完成", "已取消", "等待"],
            autopct="%1.1f%%",
        )

        self.axs[1].clear()
        self.axs[1].axis("equal")
        self.axs[1].set_title(self.title + " 低优先级")
        self.axs[1].pie(
            [agg["low complete"][0], agg["low cancel"][0], agg["low wait"][0]],
            labels=["已完成", "已取消", "等待"],
            autopct="%1.1f%%",
        )

    def calculate(self):
        result = parse_result(self.result_file_name)
        # print(result)
        # print(self.trace)
        if result.is_empty():
            return pl.DataFrame(
                [[0], [0], [1], [0], [0], [1]],
                [
                    "high complete",
                    "high cancel",
                    "high wait",
                    "low complete",
                    "low cancel",
                    "low wait",
                ],
            )

        result = result.join(self.trace, on="id", how="outer")

        agg = result.select(
            [
                pl.col("id")
                .filter((pl.col("status") == "complete") & (pl.col("prio") == 1))
                .count()
                .alias("high complete"),
                pl.col("id")
                .filter((pl.col("status") == "cancel") & (pl.col("prio") == 1))
                .count()
                .alias("high cancel"),
                pl.col("id")
                .filter(
                    (pl.col("prio") == 1)
                    & (pl.col("status") != "complete")
                    & (pl.col("status") != "cancel")
                )
                .count()
                .alias("high wait"),
                pl.col("id")
                .filter((pl.col("status") == "complete") & (pl.col("prio") == 2))
                .count()
                .alias("low complete"),
                pl.col("id")
                .filter((pl.col("status") == "cancel") & (pl.col("prio") == 2))
                .count()
                .alias("low cancel"),
                pl.col("id")
                .filter(
                    (pl.col("prio") == 2)
                    & (pl.col("status") != "complete")
                    & (pl.col("status") != "cancel")
                )
                .count()
                .alias("low wait"),
            ]
        )

        return agg


parser = argparse.ArgumentParser(description="Live Show DTP trace transport (Server)")
parser.add_argument("-t", "--trace", type=str, help="trace file", default="trace.txt")
parser.add_argument(
    "-r", "--result", type=str, help="result file", default="server.out"
)
parser.add_argument("--title", type=str, help="title", default="Live Show")

if __name__ == "__main__":
    args = parser.parse_args()

    fig, ax = plt.subplots(1, 2)
    update_date = UpdateData(ax, args.trace, args.result, args.title)
    ani = FuncAnimation(fig, update_date, interval=500)
    plt.show()
