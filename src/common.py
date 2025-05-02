import sys

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
        try:
            return { 
                p.split(":")[0]: int(p.split(":")[1]) 
                for p in prompt.strip("()").split(";") 
            }
        except:
            raise ValueError("Wrong needs/result format")
        
    def _get_delay(prompt):
        try:
            return int(prompt)
        except:
            raise ValueError("Wrong delay format")

    
    def _enrich_stocks(stocks_to_add: Dict[str, int], stocks: Dict[str, int]) -> Dict[str, int]:
        stocks_copy = stocks.copy()
        for name, _ in stocks_to_add.items():
            stocks_copy[name] = stocks_copy.get(name, 0)
        return stocks_copy

    with open(config_file) as f:
        try:
            optimize_nbr: int = 0
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("optimize:") and not optimize_nbr:
                    content = line[len("optimize:"):].strip()
                    if not content.startswith("(") or not content.endswith(")"):
                        raise ValueError(f"Malformed optimize line.")
                    optimize_nbr += 1
                    optimize_targets.extend(line[9:].strip("()").split(";"))
                    for target in optimize_targets:
                        if stocks.get(target, -1) == -1 and target != 'time':
                            raise ValueError(f"Invalid optimize target: {target}")
                elif ":" in line and "(" not in line and not optimize_nbr:
                    name, qty = line.split(":")
                    if stocks.get(name.strip(), 0):
                        raise ValueError("Duplicate stock")
                    stocks[name.strip()] = int(qty.strip())
                elif "(" in line and not optimize_nbr:
                    parts = line.split(":", maxsplit=1)
                    name = parts[0]
                    parts = parts[1].split("):(")
                    needs = _make_stock_pair(parts[0])
                    stocks = _enrich_stocks(needs, stocks)
                    parts = parts[1].split("):")
                    results = _make_stock_pair(parts[0])
                    stocks = _enrich_stocks(results, stocks)
                    delay = _get_delay(parts[1])
                    processes.append(Process(name, needs, results, delay))
                else:    
                    raise ValueError("Wrong file structure")
        except:
            sys.exit()
    
    return stocks, processes, optimize_targets