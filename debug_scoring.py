#!/usr/bin/env python3
"""Debug scoring for pirates.krpsim."""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation, Process
from src.optimizer_new import UniversalOptimizer


def main():
    config = parse_config_to_simulation('public/pirates.krpsim', 1000)
    
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
    
    optimizer = UniversalOptimizer(config.optimization_targets, all_processes, 1000)
    
    # Simulate state with some resources bought
    current_stocks = {
        'dollars': 10000,
        'boat': 1,
        'map': 5,
        'crew': 5,
        'treasure': 0,
        'reputation': 0,
        'friendship': 0
    }
    current_cycle = 200
    
    # Get available processes
    available = [p for p in config.processes if all(
        current_stocks.get(res, 0) >= qty for res, qty in p.needs.items()
    )]
    
    print(f"Current stocks: {current_stocks}")
    print(f"Current cycle: {current_cycle}")
    print(f"Available processes: {[p.name for p in available]}")
    print(f"\nHigh-value processes: {optimizer._high_value_processes}")
    print(f"Value chain resources: {optimizer._value_chain_resources}")
    print(f"Bulk targets: {optimizer._bulk_targets}")
    
    # Try to select best process
    selected = optimizer.select_best_process(available, current_stocks, current_cycle)
    
    if selected:
        print(f"\nSelected process: {selected.name}")
    else:
        print(f"\nNo process selected (all scores negative or None returned)")


if __name__ == '__main__':
    main()
