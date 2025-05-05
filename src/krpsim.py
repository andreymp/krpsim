import sys
import heapq

from typing import Dict, Tuple, List
from common import Process, parse_config

def can_run_process(process: Process, stocks: Dict[str, int]) -> bool:
    return all(stocks.get(name, 0) >= qty for name, qty in process.needs.items())

def count_score(process: Process, optimize_targets: List[str]) -> int:
    score: int = 0
    
    for target in optimize_targets:
        if target == "time":
            continue
        score += 100 * process.results.get(target, 0)
    
    score += 10 * sum(process.results.values())
    score -= process.delay
    score -= 5 * sum(process.needs.values())
    return score

def run_process(
        process: Process, 
        stocks: Dict[str, int], 
        processes_in_progress: List[Tuple[int, Process]],
        cycle_nbr: int,
        timeline: List[Tuple[int, str]]
) -> None:
    for name, qty in process.needs.items():
        stocks[name] -= qty
    
    heapq.heappush(processes_in_progress, (cycle_nbr + process.delay, process))
    timeline.append((cycle_nbr, process.name))

def simulate(
        stocks: Dict[str, int], 
        processes: List[Process],   
        optimize_targets: List[str], 
        delay: int
) -> Tuple[List[Tuple[int, str]], Dict[str, int], int]:
    cycle_nbr: int = 0
    timeline: List[Tuple[int, str]] = []
    processes_in_progress: List[Tuple[int, Process]] = []

    while cycle_nbr < delay:
        terminate_ongoing_processes(processes_in_progress, cycle_nbr, stocks)
        ready_to_start_processes: List[Process] = [ proc for proc in processes if can_run_process(proc, stocks) ]

        if not ready_to_start_processes and not processes_in_progress:
            break

        if ready_to_start_processes:
            ready_to_start_processes.sort(key=lambda proc: count_score(proc, optimize_targets), reverse=True)
            for process in ready_to_start_processes:
                while can_run_process(process, stocks):
                    run_process(process, stocks, processes_in_progress, cycle_nbr, timeline)
        
        cycle_nbr += 1
        if cycle_nbr == delay:
            print("Timeout :(")
    
    return timeline, stocks, cycle_nbr

def show(timeline: List[Tuple[int, str]], stocks: Dict[str, int], cycle_nbr: int) -> None:
    print("Main walk")

    with open("public/result_set.txt", "w") as result_set:
        for time, process_name in timeline:
            line: str = f"{time}:{process_name}"
            result_set.write(f"{line}\n")
            print(line)
    
        result_set.write(f"{cycle_nbr}\n")
        print(f"no more process doable at time {cycle_nbr}")
    
    print("Stock :")
    for name, qty in stocks.items():
        print(f"{name} => {qty}")

def terminate_ongoing_processes(
        processes_in_progress: List[Tuple[int, Process]],
        cycle_nbr: int,
        stocks: Dict[str, int]
) -> None:
    while processes_in_progress and processes_in_progress[0][0] == cycle_nbr:
        _, process = heapq.heappop(processes_in_progress)
        
        for name, qty in process.results.items():
            print('here')
            stocks[name] = stocks.get(name, 0) + qty

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Wrong number of arguments")
        sys.exit()
    
    config_file: str = sys.argv[1]
    if not config_file.endswith(".krpsim"):
        print("Wrong file extension")
        sys.exit()
    
    delay: int = int(sys.argv[2])
    stocks, processes, optimize_targets = parse_config(config_file)
    print(f"Nice file! {len(processes)} processes, {len(stocks)} stocks, {len(optimize_targets)} to optimize")
    timeline, stocks, cycle_nbr = simulate(stocks, processes, optimize_targets, delay)
    print("Evaluating .................. done.")
    show(timeline, stocks, cycle_nbr)
