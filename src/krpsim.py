import sys

from collections import defaultdict
from typing import Dict, Tuple, List

class Process:
    def __init__(self, name: str, needs: Dict[str, int], results: Dict[str, int], delay: int):
        self.name:str = name
        self.needs: Dict[str, int] = needs
        self.results: Dict[str, int] = results
        self.delay: int = delay
        self.start_times: List[int] = []


def parse(config_file: str) -> Tuple[Dict[str, int], List[Process], List[str]]:
    stocks: Dict[str, int] = {}
    processes: List[Process] = []
    optimize_targets: List[str] = []

    def _make_stock_pair(prompt: str) -> Dict[str, int]:
        return { 
            p.split(":")[0]: int(p.split(":")[1]) 
            for p in prompt.strip("()").split(";") 
        }
    
    def _enrich_stocks(stocks_to_add: Dict[str, int], stocks: Dict[str, int]) -> Dict[str, int]:
        stocks_copy = stocks.copy()
        for name, _ in stocks_to_add.items():
            stocks_copy[name] = stocks_copy.get(name, 0)
        return stocks_copy

    with open(config_file) as f:
        optimize_nbr: int = 0
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("optimize:"):
                optimize_nbr += 1
                optimize_targets.extend(line[9:].strip("()").split(";"))
            elif ":" in line and "(" not in line:
                name, qty = line.split(":")
                stocks[name.strip()] = int(qty.strip())
            elif "(" in line:
                parts = line.split(":", maxsplit=1)
                name = parts[0]
                parts = parts[1].split("):(")
                needs = _make_stock_pair(parts[0])
                stocks = _enrich_stocks(needs, stocks)
                parts = parts[1].split("):")
                results = _make_stock_pair(parts[0])
                stocks = _enrich_stocks(results, stocks)
                delay = int(parts[1])
                processes.append(Process(name, needs, results, delay))
            else:    
                print("Warning: Unknown prompt")

        if optimize_nbr != 1:
            print("Only one optimisation line should be presented")
            sys.exit()
    
    return stocks, processes, optimize_targets

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
