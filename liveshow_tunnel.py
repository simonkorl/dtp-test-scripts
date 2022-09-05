import argparse
import re
from turtle import update
from typing import Any, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.animation import FuncAnimation
from matplotlib.axes import Axes
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

plt.rcParams["font.sans-serif"] = ["Noto Sans CJK JP"]

regex_fec = re.compile(
    r"""\[INFO\]\ quiche:\ 
    redundancy\ rate:\ (\d+\.\d+),\ 
    rtt:\ (\d+\.\d+),\ 
    pacing_rate:\ (\d+\.\d+),\ 
    remaining_time:\s*(\d+(\.\d+)?),\ 
    predict_loss_rate:\ (\d+(\.\d+)?),\ 
    FEC:\ (\d)\ ([ \w]+)
    """,
    re.VERBOSE,
)


def parse_log(log_file_name: str) -> Tuple[pl.DataFrame, List[Any]]:
    data = []
    try:
        with open(log_file_name, "r") as log_file:
            for line in log_file:
                if (match := regex_fec.match(line)) is not None:
                    data.append(
                        [
                            float(match.group(1)),
                            float(match.group(2)),
                            float(match.group(3)),
                            float(match.group(4)),
                            float(match.group(6)),
                            int(match.group(8)),
                            # match.group(9),
                        ]
                    )
                else:
                    continue

        df = pl.DataFrame(
            data,
            columns=[
                "redundancy_rate",
                "rtt",
                "pacing_rate",
                "remaining_time",
                "predict_loss_rate",
                "fec",
                # "fec_note",
            ],
        )

        return (df, data[-1])
    except:
        return (
            pl.DataFrame(
                None,
                columns=[
                    "redundancy_rate",
                    "rtt",
                    "pacing_rate",
                    "remaining_time",
                    "predict_loss_rate",
                    "fec",
                    # "fec_note",
                ],
            ),
            [],
        )


class UpdateData:
    def __init__(self, ax: Axes, ax_btm: Axes, log_file_name: str):
        self.ax = ax
        self.ax_btm = ax_btm
        self.log_file_name = log_file_name
        self.lines = []
        self.lines.append(self.ax[0, 1].plot([], [])[0])
        self.lines.append(self.ax[1, 1].plot([], [])[0])

        self.ax[0, 0].set_axis_off()
        self.ax[0, 0].text(0.5, 0.5, "RTT", size="x-large", weight="bold")
        self.ax[1, 0].set_axis_off()
        self.ax[1, 0].text(0.5, 0.5, "估计丢包率", size="x-large", weight="bold")
        self.ax_btm.set_axis_off()
        self.text = self.ax_btm.text(0.2, 0.5, "当前 FEC 状态：无数据", size="x-large")
        self.circle = self.ax_btm.add_patch(
            mpatches.Ellipse((0.1, 0.55), width=0.05, height=0.2, color="tab:gray")
        )

    def __call__(self, frame):
        df, last = parse_log(self.log_file_name)

        rtt = df["rtt"].to_numpy()
        loss_rate = df["predict_loss_rate"].to_numpy()
        x = np.arange(len(df))

        # print(x, rtt, loss_rate)

        self.lines[0].set_data(x, rtt)
        self.lines[1].set_data(x, loss_rate)
        self.ax[0, 1].set_xlim(0, len(x) + 1)
        self.ax[0, 1].set_ylim(0, max(rtt) + 1)
        self.ax[1, 1].set_xlim(0, len(x) + 1)
        self.ax[1, 1].set_ylim(0, np.max(loss_rate))

        if last[-1] == 0:
            self.text.set_text("目前 FEC 状态：启用，时间不足")
            self.circle.set_color("tab:red")
        elif last[-1] == 1:
            self.text.set_text("目前 FEC 状态：启用，带宽充裕")
            self.circle.set_color("tab:orange")
        elif last[-1] == 2:
            self.text.set_text("目前 FEC 状态：未启用")
            self.circle.set_color("tab:green")
        else:
            print("what?")

        return [self.lines, self.text]

    def calculate(self):
        pass


parser = argparse.ArgumentParser(description="Live Show DTP tunnel transport")
parser.add_argument("-l", "--log", type=str, help="log file name")

if __name__ == "__main__":
    args = parser.parse_args()

    parse_log(args.log)

    # print("hello")

    # fig, ax = plt.subplots(3, 3)
    fig = plt.figure(constrained_layout=True)
    gs = GridSpec(3, 3, figure=fig)

    # gs = ax[2, 0].get_gridspec()
    # for a in ax[2, 0:]:
    #     a.remove()
    ax = np.array(
        [
            [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1:])],
            [fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1:])],
        ]
    )
    ax_btm = fig.add_subplot(gs[2, 0:])
    update_data = UpdateData(ax, ax_btm, args.log)
    anim = FuncAnimation(fig, update_data, interval=1000)
    plt.show()
