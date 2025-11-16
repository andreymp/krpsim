#!/usr/bin/env python3
"""Test process selection in first few cycles"""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation
from src.optimizer_new import UniversalOptimizer

# Load config
config = parse_config_to_simulation("public/pomme.krpsim", 50000)

# Create optimizer
optimizer = UniversalOptimizer(
    optimization_targets=config.optimization_targets,
    all_processes=config.processes,
    total_cycles=50000
)

print(f"Optimizer analyzed: {optimizer._analyzed}")
print(f"High-value processes: {optimizer._high_value_processes}")
print(f"Euro reserve: {optimizer._target_reserve_needed.get('euro', 0):,}")

# Simulate first cycle selection
initial_stocks = {'euro': 10000, 'four': 10}

# Get all processes that can execute
executable = [p for p in config.processes if all(initial_stocks.get(r, 0) >= q for r, q in p.needs.items())]

print(f"\nExecutable processes at cycle 0: {len(executable)}")
for p in executable:
    print(f"  {p.name}")

# Select best process
best = optimizer.select_best_process(executable, initial_stocks, 0)

print(f"\nBest process selected: {best.name if best else 'None'}")

if best:
    score = optimizer.calculate_priority_score(best, initial_stocks, 0)
    print(f"Score: {score:,.2f}")
    print(f"Needs: {best.needs}")
    print(f"Results: {best.results}")
