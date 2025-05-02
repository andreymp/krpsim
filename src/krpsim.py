import sys

from collections import defaultdict
from typing import Dict, Tuple, List
from common import Process, parse

def simulate(
        stocks: Dict[str, int], 
        processes: List[Process],   
        optimize_targets: List[str], 
        delay: int
) -> Tuple[defaultdict[list], Dict[str, int], int]:
    cycle_nbr: int = 0
    timeline = defaultdict(list)
    event_in_progress: List[Tuple[int, Process]] = []

    while cycle_nbr < delay:
        # finishing the processes
        process_stopped: bool = False
        for end_cycle, process in list(event_in_progress):
            if (end_cycle == cycle_nbr):
                for name, qty in process.results.items():
                    stocks[name] = stocks.get(name, 0) + qty
                event_in_progress.remove((end_cycle, process))
                process_stopped = True
        
        # looking for processes to start
        process_started:  bool = False
        for process in processes:
            if all(stocks.get(name, 0) >= qty for name, qty in process.needs.items()):
                # optimize targets process
                for target in optimize_targets:
                    if process.results.get(target, 0):
                        for name, qty in process.needs.items():
                            stocks[name] -= qty
                        process.start_times.append(cycle_nbr)
                        event_in_progress.append((cycle_nbr + process.delay, process))
                        timeline[cycle_nbr].append(process.name) 
                        process_started = True

                # start the process
                if not process_started:
                    for name, qty in process.needs.items():
                            stocks[name] -= qty
                    process.start_times.append(cycle_nbr)
                    event_in_progress.append((cycle_nbr + process.delay, process))
                    timeline[cycle_nbr].append(process.name) 
                    process_started = True
                
        if not process_stopped and not process_started and not event_in_progress:
            break

        cycle_nbr += 1

        if cycle_nbr == delay:
            print("Timeout :(")
            break
    
    return timeline, stocks, cycle_nbr

def show(timeline: defaultdict[list], stocks: Dict[str, int], cycle_nbr: int) -> None:
    print("Main walk")
    for time in sorted(timeline.keys()):
        for process in timeline[time]:
            print(f"{time}:{process}")
    print(f"no more process doable at time {cycle_nbr}")
    print("Stock :")
    for name, qty in stocks.items():
        print(f"{name} => {qty}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Wrong number of arguments")
        sys.exit()
    
    config_file: str = sys.argv[1]
    if not config_file.endswith(".krpsim"):
        print("Wrong file extension")
        sys.exit()
    
    delay: int = int(sys.argv[2])
    stocks, processes, optimize_targets = parse(config_file)
    print(f"Nice file! {len(processes)} processes, {len(stocks)} stocks, {len(optimize_targets)} to optimize")
    timeline, stocks, cycle_nbr = simulate(stocks, processes, optimize_targets, delay)
    print("Evaluating .................. done.")
    show(timeline, stocks, cycle_nbr)
