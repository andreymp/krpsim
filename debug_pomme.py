#!/usr/bin/env python3
"""Debug pomme.krpsim."""

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
    
    print(f"Optimization targets: {config.optimization_targets}")
    print(f"High-value processes: {optimizer._high_value_processes}")
    print(f"Value chain resources: {optimizer._value_chain_resources}")
    print(f"Value chain depth: {optimizer._value_chain_depth}")
    print(f"Bulk targets: {optimizer._bulk_targets}")
    print(f"Execution multiplier: {optimizer._execution_multiplier}")
    print(f"Adaptive bulk multiplier: {optimizer._calculate_adaptive_bulk_multiplier(all_processes)}")
    
    # Check vente_boite specifically
    for p in all_processes:
        if 'vente' in p.name:
            print(f"\nProcess: {p.name}")
            print(f"  Needs: {p.needs}")
            print(f"  Results: {p.results}")
            print(f"  Is high-value: {p.name in optimizer._high_value_processes}")


if __name__ == '__main__':
    main()
