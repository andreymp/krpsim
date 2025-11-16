#!/usr/bin/env python3
"""
Debug script to understand optimizer behavior on pomme.krpsim
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.common import parse_config_to_simulation
from src.optimizer_new import UniversalOptimizer


def debug_optimizer():
    """Debug the optimizer's analysis of pomme.krpsim"""
    
    print("=" * 80)
    print("OPTIMIZER DEBUG - pomme.krpsim")
    print("=" * 80)
    
    # Load configuration
    config = parse_config_to_simulation("public/pomme.krpsim", 50000)
    
    # Create optimizer with all processes
    optimizer = UniversalOptimizer(
        optimization_targets=config.optimization_targets,
        all_processes=config.processes,
        total_cycles=50000
    )
    
    print(f"\nOptimization targets: {config.optimization_targets}")
    print(f"Total cycles: 50000")
    print(f"Execution multiplier: {optimizer._execution_multiplier}")
    print(f"Is long simulation: {optimizer._is_long_simulation}")
    print(f"Gathering limit cycle: {optimizer._gathering_limit_cycle}")
    
    print(f"\n" + "=" * 80)
    print("HIGH-VALUE PROCESSES")
    print("=" * 80)
    
    if optimizer._high_value_processes:
        for hv_name in optimizer._high_value_processes:
            print(f"\n{hv_name}:")
            # Find the process
            for process in config.processes:
                if process.name == hv_name:
                    print(f"  Needs: {process.needs}")
                    print(f"  Results: {process.results}")
                    print(f"  Delay: {process.delay}")
                    
                    # Calculate net production
                    for target in config.optimization_targets:
                        if target in process.results:
                            production = process.results[target]
                            consumption = process.needs.get(target, 0)
                            net = production - consumption
                            print(f"  Net {target} production: {net}")
                    break
    else:
        print("No high-value processes identified!")
    
    print(f"\n" + "=" * 80)
    print("VALUE CHAIN RESOURCES")
    print("=" * 80)
    
    if optimizer._value_chain_resources:
        print(f"\nTotal value chain resources: {len(optimizer._value_chain_resources)}")
        for resource in sorted(optimizer._value_chain_resources):
            depth = optimizer._value_chain_depth.get(resource, 0)
            bulk_target = optimizer._bulk_targets.get(resource, 0)
            print(f"  {resource}: depth={depth}, bulk_target={bulk_target}")
    else:
        print("No value chain resources identified!")
    
    print(f"\n" + "=" * 80)
    print("INTERMEDIATE NEEDS")
    print("=" * 80)
    
    if optimizer._intermediate_needs:
        for proc_name, needs in optimizer._intermediate_needs.items():
            print(f"\n{proc_name}:")
            for resource, quantity in needs.items():
                print(f"  {resource}: {quantity}")
    else:
        print("No intermediate needs identified!")
    
    print(f"\n" + "=" * 80)
    print("TARGET RESERVES")
    print("=" * 80)
    
    if optimizer._target_reserve_needed:
        for target, reserve in optimizer._target_reserve_needed.items():
            print(f"  {target}: {reserve:,}")
    else:
        print("No target reserves calculated!")
    
    print(f"\n" + "=" * 80)
    print("BULK TARGETS")
    print("=" * 80)
    
    if optimizer._bulk_targets:
        for resource, target in sorted(optimizer._bulk_targets.items(), key=lambda x: x[1], reverse=True):
            print(f"  {resource}: {target:,}")
    else:
        print("No bulk targets calculated!")
    
    print(f"\n" + "=" * 80)


if __name__ == "__main__":
    debug_optimizer()
