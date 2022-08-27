import csv
import re

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("file", type=str, help="file to parse")

regex_start = re.compile(
    r"""(\d+),      # block_id
        start,      # start status
        (\d+)       # duration
    """,
    re.VERBOSE,
)
regex_complete = re.compile(
    r"""\[INFO\]\ quiche:\ stream\ 
        (\d+)       # block_id
        \ send\ complete,
        (\d+)       # duration
    """,
    re.VERBOSE,
)
regex_cancelled = re.compile(
    r"""\[INFO\]\ quiche::scheduler::dtp_scheduler:\ block\ 
        (\d+)       # block_id
        \ is\ canceled,\ passed\ 
        (\d+),      # passed time
        (\d+)       # duration
    """,
    re.VERBOSE,
)

if __name__ == "__main__":
    args = parser.parse_args()

    data = {}

    m = re.match(regex_start, "1,start,100")

    print("hello world")

    with open(args.file, "r") as f:
        for line in f:
            if line.startswith("block_id"):
                continue
            elif (match := regex_start.match(line)) is not None:
                if match.group(1) not in data:
                    data[match.group(1)] = {}
                data[match.group(1)]["start"] = int(match.group(2))
            elif (match := regex_complete.match(line)) is not None:
                if match.group(1) not in data:
                    data[match.group(1)] = {}
                data[match.group(1)]["complete"] = int(match.group(2))
            elif (match := regex_cancelled.match(line)) is not None:
                if match.group(1) not in data:
                    data[match.group(1)] = {}
                data[match.group(1)]["cancelled"] = int(match.group(3))
                data[match.group(1)]["cancelled_passed"] = int(match.group(2))
            else:
                continue

    with open(args.file + ".csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["block_id", "start", "complete", "cancelled", "cancelled_passed"]
        )
        for k, v in data.items():
            writer.writerow(
                [
                    k,
                    v.get("start", None),
                    v.get("complete", None),
                    v.get("cancelled", None),
                    v.get("cancelled_passed", None),
                ]
            )
