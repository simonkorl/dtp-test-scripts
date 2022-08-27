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


def parse_server_log(server_log_file_name: str) -> pl.DataFrame:
    """
    # parse_server_log

    Parse a server log file and return a polars DataFrame.

        Parameters:
            server_log_file_name (str): The name of the server log file.

        Returns:
            polars.DataFrame: The parsed server log.

    Format of the server log file:
        CSV file with following columns:
        - block_id
        - start
        - complete
        - cancelled
        - cancelled_passed
    """
    try:
        server_log = pl.read_csv(server_log_file_name)
        server_log["block_id"] = server_log["block_id"].apply(lambda x: (x >> 2) - 1)
        return server_log
    except:
        return pl.DataFrame(
            None, ["block_id", "start", "complete", "cancelled", "cancelled_passed"]
        )


class UpdateData:
    def __init__(
        self,
        ax: Axes,
        trace_file_name: str,
        result_file_name: str,
        server_file_name: str,
        title: str,
        playback: bool,
    ):
        self.trace = parse_trace(trace_file_name)
        self.result_file_name = result_file_name
        self.server_log = parse_server_log(server_file_name)
        self.playback = playback
        self.timer = 0
        self.ax = ax
        self.lines = []
        for i in range(2):
            self.lines.append(self.ax.plot([], [], label=f"Prio {i}")[0])
        for i in range(2):
            self.lines.append(self.ax.plot([], [], label=f"Prio {i} unsent")[0])
        self.table = self.ax.table(
            colLabels=("整体", "高优先", "低优先"),
            rowLabels=["块到达率", "平均块完成时间"],
            cellText=[["NA", "NA", "NA"], ["NA", "NA", "NA"]],
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
        self.timer += 500
        x, y = self.calculate()
        self.lines[0].set_data(x, y[1])
        self.lines[1].set_data(x, y[2])
        if self.playback:
            self.lines[2].set_data(x, y[4])
            self.lines[3].set_data(x, y[5])
        # print(x)
        xlim = max(np.max(x) * 1.1, 1)
        self.ax.set_xlim(0, xlim)
        return self.lines

    def calculate(self):
        # 一个简单粗暴的版本，没有增量更新
        # 其实可以做，但是直接复制比较无脑
        result = parse_result(self.result_file_name)
        if self.playback:
            result = result.filter(pl.col("duration") / 1000 < self.timer)

        if result.is_empty():
            self.table[1, 0].get_text().set_text("NA")
            self.table[1, 1].get_text().set_text("NA")
            self.table[1, 2].get_text().set_text("NA")
            self.table[2, 0].get_text().set_text("NA")
            self.table[2, 1].get_text().set_text("NA")
            self.table[2, 2].get_text().set_text("NA")
            return np.array([0]), np.array([[], [], [], [], [], []])

        result = result.join(self.trace, left_on="block_id", right_on="id", how="outer")

        agg = result.select(
            [
                # 平均 bct
                pl.col("bct").filter(pl.col("bct") < 1000000).mean().alias("avg"),
                # 高优先平均 bct
                pl.col("bct")
                .filter((pl.col("bct") < 1000000) & (pl.col("prio") == 1))
                .mean()
                .alias("high"),
                # 低优先平均 bct
                pl.col("bct")
                .filter((pl.col("bct") < 1000000) & (pl.col("prio") == 2))
                .mean()
                .alias("low"),
                # 到达率
                (
                    pl.col("bct").filter(pl.col("bct") < pl.col("ddl")).count()
                    / pl.col("bct").count()
                ).alias("arrive"),
                # 高优先到达率
                (
                    pl.col("bct")
                    .filter((pl.col("prio") == 1) & (pl.col("bct") < pl.col("ddl")))
                    .count()
                    / pl.col("bct").filter(pl.col("prio") == 1).count()
                ).alias("high arrive"),
                # 低优先到达率
                (
                    pl.col("bct")
                    .filter((pl.col("prio") == 2) & (pl.col("bct") < pl.col("ddl")))
                    .count()
                    / pl.col("bct").filter(pl.col("prio") == 2).count()
                ).alias("low arrive"),
            ]
        )

        self.table[1, 0].get_text().set_text(
            "{:.2f}%".format(agg["arrive"][0] * 100) if agg["arrive"][0] else "NA"
        )
        self.table[1, 1].get_text().set_text(
            "{:.2f}%".format(agg["high arrive"][0] * 100)
            if agg["high arrive"][0]
            else "NA"
        )
        self.table[1, 2].get_text().set_text(
            "{:.2f}%".format(agg["low arrive"][0] * 100)
            if agg["low arrive"][0]
            else "NA"
        )
        self.table[2, 0].get_text().set_text(
            "{:.2f}ms".format(agg["avg"][0]) if agg["avg"][0] else "NA"
        )
        self.table[2, 1].get_text().set_text(
            "{:.2f}ms".format(agg["high"][0]) if agg["high"][0] else "NA"
        )
        self.table[2, 2].get_text().set_text(
            "{:.2f}ms".format(agg["low"][0]) if agg["low"][0] else "NA"
        )

        if self.playback:
            result = result.join(
                self.server_log, on="block_id", how="outer", suffix="_s"
            )
            result = result.select(
                [
                    (pl.col("bct") < pl.col("ddl")).alias("intime"),
                    # (pl.col("duration") == None).alias("unsent"),
                    "block_id",
                    "prio",
                    "bct",
                    "duration",
                    "complete",
                    "cancelled",
                    (pl.col("ddl") / 1000 + pl.col("start_s") / 1000000).alias(
                        "timestamp"
                    ),
                ]
            ).filter(pl.col("timestamp") * 1000 < self.timer)
            if result.is_empty():
                self.table[1, 0].get_text().set_text("NA")
                self.table[1, 1].get_text().set_text("NA")
                self.table[1, 2].get_text().set_text("NA")
                self.table[2, 0].get_text().set_text("NA")
                self.table[2, 1].get_text().set_text("NA")
                self.table[2, 2].get_text().set_text("NA")
                return np.array([0]), np.array([[], [], [], [], [], []])

            # print(result)

            x = result["timestamp"].to_numpy()
            y = np.zeros((6, len(x)))
            y_count = np.zeros(3)
            y_intime = np.zeros(3)
            y_unsent = np.zeros(3)
            qoe = 0
            qoe_theory = 0
            for i in range(len(x)):
                y_count[result["prio"][i]] += 1
                qoe_theory += 0.9 * (3 - result["prio"][i]) / 2 + 0.1
                if result["intime"][i]:
                    y_intime[result["prio"][i]] += 1
                    qoe += 0.9 * (3 - result["prio"][i]) / 2 + 0.1
                if result["cancelled"][i]:
                    y_unsent[result["prio"][i]] += 1
                for j in range(3):
                    y[j][i] = y_intime[j] / y_count[j] if y_count[j] > 0 else None
                    y[j + 3][i] = y_unsent[j] / y_count[j] if y_count[j] > 0 else None

            print(
                "qoe {qoe} qoe_theory {qoe_theory}".format(
                    qoe=qoe, qoe_theory=qoe_theory
                )
            )

            return x, y
        else:
            result = (
                result.filter(pl.col("duration") != None)
                .select(
                    [
                        "block_id",
                        (pl.col("bct") < pl.col("ddl")).alias("intime"),
                        "prio",
                        "ddl",
                        (pl.col("ddl") / 1000 + pl.col("start")).alias("timestamp"),
                    ]
                )
                .sort("timestamp")
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
                    y[j][i] = y_intime[j] / y_count[j] if y_count[j] > 0 else None

            return x, y


parser = argparse.ArgumentParser(description="Live Show DTP trace transport")
parser.add_argument("-t", "--trace", type=str, help="trace file", default="trace.txt")
parser.add_argument(
    "-r", "--result", type=str, help="result file", default="result.csv"
)
parser.add_argument(
    "-s", "--server-log", type=str, help="server log file", default="server.csv"
)
parser.add_argument("--title", type=str, help="title", default="Live Show")
parser.add_argument("--playback", type=bool, help="playback", default=False)

if __name__ == "__main__":
    args = parser.parse_args()

    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.3)
    update_data = UpdateData(
        ax, args.trace, args.result, args.server_log, args.title, args.playback
    )
    anim = FuncAnimation(fig, update_data, interval=500)
    plt.show()
