import argparse
import csv

import utils


def find_unsend(result_file_name, trace_file_name):
    if trace_file_name is not None:
        block_num = utils.count_newlines(trace_file_name)
        trace = set(range(block_num))

        with open(result_file_name, "r") as f:
            reader = csv.reader(f)
            result = [((int(row[0]) - 1) >> 2) - 1 for row in reader]

        return sorted([(x, ((x + 1) << 2) + 1) for x in trace - set(result)])
    else:
        raise Exception("trace_file_name is None")


parser = argparse.ArgumentParser(description="Analyze result")
parser.add_argument("command", metavar="cmd", type=str, choices=["find_unsend", "hist"])
parser.add_argument(
    "result_file",
    metavar="res",
    type=str,
    help="result files to analyze",
)
parser.add_argument("-t", "--trace_file", metavar="trace", type=str, help="trace file")

if __name__ == "__main__":
    args = parser.parse_args()

    match args.command:
        case "find_unsend":
            print(find_unsend(args.result_file, args.trace_file))
        case "hist":
            raise Exception("Not implemented")
        case _:
            raise Exception("Unknown command")
