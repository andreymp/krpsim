import sys

from typing import Tuple, Dict, List
from common import parse_config, Process
from collections import defaultdict

def parse_result_set(result_set_file: str) -> Tuple[defaultdict[list], int]:
    timeline: defaultdict[list] = defaultdict(list)
    final_time: int = 0

    with open(result_set_file) as f:
        for line in f:
            if ':' in line:
                time_str, process = line.strip().split(":")
                time = int(time_str)
                timeline[time].append(process)
                last_time = max(last_time, time)

    return timeline, final_time

def verify(
        stocks: Dict[str, int],
        processes: List[Process],
        optimize_targets: List[str],
        timeline: defaultdict[list],
        final_time: int) -> None:
    print("Verifying...")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Wrong number of arguments")
        sys.exit()
    
    config_file: str = sys.argv[1]
    if not config_file.endswith(".krpsim"):
        print("Wrong config file extension")
        sys.exit()
    
    result_set = sys.argv[2]
    if not config_file.endswith(".txt"):
        print("Wrong result set file extension")
        sys.exit()

    print("Parsing config file and validating result set...")
    stocks, processes, optimize_targets = parse_config(config_file)
    timeline, final_time = parse_result_set(result_set)
    print("Evaluating .................. done.")
    verify(stocks, processes, optimize_targets, timeline, final_time)
