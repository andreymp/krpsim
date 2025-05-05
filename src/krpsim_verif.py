import sys
import heapq

from typing import Tuple, Dict, List
from common import parse_config, Process

def parse_result_set(result_set_file: str) -> Tuple[List[Tuple[int, str]], int]:
    timeline: List[Tuple[int, str]] = []
    end_cycle_nbr: int = 0

    with open(result_set_file) as f:
        for line in f:
            if ':' in line:
                time, process_name = line.strip().split(":")
                timeline.append((int(time), process_name))
            else:
                end_cycle_nbr = int(line)

    return timeline, end_cycle_nbr

def verify(
        stocks: Dict[str, int],
        processes: List[Process],
        timeline: List[Tuple[int, str]],
        end_cycle_nbr: int) -> bool:
    processes_in_progress: List[Tuple[int, Process]] = []
    idx: int = 0

    for cycle_nbr, process_name in timeline:
        while idx < cycle_nbr:
            idx += 1
            terminate_ongoing_processes(processes_in_progress, idx, stocks)

        process_as_list: List[Process] = [ proc for proc in processes if proc.name == process_name ]
        if not process_as_list:
            print(f"Error: Unknown process '{process_name}' at {cycle_nbr}")
            return False
        
        process = process_as_list[0]
        for name, qty in process.needs.items():
            if stocks.get(name, 0) < qty:
                print(f"Error at {cycle_nbr}: not enough '{name}' for process '{process.name}'")
                return False
            stocks[name] -= qty

        heapq.heappush(processes_in_progress, (cycle_nbr + process.delay, process))
        idx = cycle_nbr
        
    while processes_in_progress:
        idx += 1
        terminate_ongoing_processes(processes_in_progress, idx, stocks)
    
    if idx != end_cycle_nbr:
        print("The finish time does not correspond")
        return False

    return True

def terminate_ongoing_processes(
        processes_in_progress: List[Tuple[int, Process]],
        cycle_nbr: int,
        stocks: Dict[str, int]
) -> None:
    while processes_in_progress and processes_in_progress[0][0] == cycle_nbr:
        _, process = heapq.heappop(processes_in_progress)
        
        for name, qty in process.results.items():
            stocks[name] = stocks.get(name, 0) + qty

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Wrong number of arguments")
        sys.exit()
    
    config_file: str = sys.argv[1]
    if not config_file.endswith(".krpsim"):
        print("Wrong config file extension")
        sys.exit()
    
    result_set = sys.argv[2]
    if not result_set.endswith(".txt"):
        print("Wrong result set file extension")
        sys.exit()

    print("Parsing config file and validating result set...")
    stocks, processes, _ = parse_config(config_file)
    timeline, final_time = parse_result_set(result_set)
    print("Evaluating .................. done.")
    is_correct = verify(stocks, processes, timeline, final_time)
    print("Validation completed :)" if is_correct else "Validation failed :(")
