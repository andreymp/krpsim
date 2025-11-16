#!/usr/bin/env python3
"""Debug cash-flow mode for pomme.krpsim."""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation, Process
from src.optimizer_new import UniversalOptimizer


def main():
    config = parse_config_to_simulation('public/pomme.krpsim', 50000)
    
    # Create optimizer
    all_processes = [
        Process(
            name=p.name,
            needs=p.needs,
            results=p.results,
            delay=p.delay
        )
        for p in config.processes
    ]
    
    optimizer = UniversalOptimizer(config.optimization_targets, all_processes, 50000)
    
    # Simulate state at cycle 1092 (when it stalls)
    current_stocks = {
        'four': 10,
        'euro': 11400,
        'pomme': 340,
        'citron': 300,
        'oeuf': 0,
        'farine': 0,
        'beurre': 1964,
        'lait': 1948,
        'jaune_oeuf': 4,
        'blanc_oeuf': 76,
        'pate_sablee': 0,
        'pate_feuilletee': 0,
        'tarte_citron': 0,
        'tarte_pomme': 6,
        'flan': 5,
        'boite': 0
    }
    current_cycle = 1092
    
    # Get available processes
    available = [p for p in config.processes if all(
        current_stocks.get(res, 0) >= qty for res, qty in p.needs.items()
    )]
    
    print(f"Current stocks: {current_stocks}")
    print(f"Current cycle: {current_cycle}")
    print(f"Available processes: {[p.name for p in available]}")
    print(f"\nCash-flow mode: {optimizer._cash_flow_mode}")
    print(f"Stuck counter: {optimizer._stuck_counter}")
    print(f"Current phase: {optimizer._current_phase}")
    
    # Check euro reserve
    euro_reserve = optimizer._get_effective_reserve('euro', current_cycle)
    print(f"Euro reserve: {euro_reserve}")
    print(f"Available euro (after reserve): {current_stocks.get('euro', 0) - euro_reserve}")
    
    # Score each available process
    print(f"\nProcess scores:")
    for process in available:
        score = optimizer.calculate_priority_score(process, current_stocks, current_cycle)
        print(f"  {process.name}: {score:.2f}")
    
    # Manually check what select_best_process does
    print(f"\nManual selection simulation:")
    
    # Check bottleneck producers
    print(f"Checking for bottleneck producers...")
    
    # Try to select best process
    selected = optimizer.select_best_process(available, current_stocks, current_cycle)
    
    print(f"\nAfter select_best_process:")
    print(f"  Returned: {selected.name if selected else 'None'}")
    
    if selected:
        print(f"\nSelected process: {selected.name}")
    else:
        print(f"\nNo process selected")
        print(f"Cash-flow mode after selection: {optimizer._cash_flow_mode}")
        print(f"Stuck counter after selection: {optimizer._stuck_counter}")


if __name__ == '__main__':
    main()
