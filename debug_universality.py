#!/usr/bin/env python3
"""
Debug script to understand optimizer behavior on different configurations.
"""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation, Process
from src.optimizer_new import UniversalOptimizer


def debug_config(config_file: str, cycles: int):
    """Debug a configuration."""
    print(f"\n{'='*60}")
    print(f"Debugging {config_file}")
    print(f"{'='*60}\n")
    
    # Load configuration
    config = parse_config_to_simulation(config_file, cycles)
    
    print(f"Initial stocks: {config.initial_stocks}")
    print(f"Optimization targets: {config.optimization_targets}")
    print(f"Number of processes: {len(config.processes)}\n")
    
    # Provide all processes for analysis
    all_processes = [
        Process(
            name=p.name,
            needs=p.needs,
            results=p.results,
            delay=p.delay
        )
        for p in config.processes
    ]
    
    # Create optimizer with all processes
    optimizer = UniversalOptimizer(config.optimization_targets, all_processes, cycles)
    
    # Print analysis results
    print(f"High-value processes: {optimizer._high_value_processes}")
    print(f"Value chain resources: {optimizer._value_chain_resources}")
    print(f"Value chain depth: {optimizer._value_chain_depth}")
    print(f"Bulk targets: {optimizer._bulk_targets}")
    print(f"Target reserves: {optimizer._target_reserve_needed}")
    
    # Simulate first few selections
    print(f"\nSimulating first 10 process selections:")
    current_stocks = config.initial_stocks.copy()
    current_cycle = 0
    
    for i in range(10):
        available = [p for p in config.processes if all(
            current_stocks.get(res, 0) >= qty for res, qty in p.needs.items()
        )]
        
        if not available:
            print(f"  Cycle {current_cycle}: No available processes")
            break
        
        selected = optimizer.select_best_process(available, current_stocks, current_cycle)
        
        if selected is None:
            print(f"  Cycle {current_cycle}: Optimizer returned None")
            break
        
        print(f"  Cycle {current_cycle}: Selected {selected.name}")
        
        # Update stocks
        for res, qty in selected.needs.items():
            current_stocks[res] = current_stocks.get(res, 0) - qty
        for res, qty in selected.results.items():
            current_stocks[res] = current_stocks.get(res, 0) + qty
        
        current_cycle += selected.delay
    
    print(f"\nFinal stocks after 10 selections: {current_stocks}")


if __name__ == '__main__':
    debug_config('public/ikea.krpsim', 1000)
    debug_config('public/pirates.krpsim', 1000)
    debug_config('public/mtrazzi.krpsim', 1000)
