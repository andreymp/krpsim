#!/usr/bin/env python3
"""Test scoring logic for buy_pomme process"""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation, Process
from src.optimizer_new import UniversalOptimizer

# Load config
config = parse_config_to_simulation("public/pomme.krpsim", 50000)

# Create optimizer
optimizer = UniversalOptimizer(
    optimization_targets=config.optimization_targets,
    all_processes=config.processes,
    total_cycles=50000
)

# Find buy_pomme process
buy_pomme = None
for p in config.processes:
    if p.name == "buy_pomme":
        buy_pomme = p
        break

print(f"Testing buy_pomme process:")
print(f"  Needs: {buy_pomme.needs}")
print(f"  Results: {buy_pomme.results}")
print(f"  Delay: {buy_pomme.delay}")

# Test scoring at cycle 0 with initial stocks
initial_stocks = {'euro': 10000, 'four': 10}
score = optimizer.calculate_priority_score(buy_pomme, initial_stocks, 0)

print(f"\nScore at cycle 0 with 10,000 euros: {score:,.2f}")
print(f"Euro reserve needed: {optimizer._target_reserve_needed.get('euro', 0):,}")
print(f"Available euros: {initial_stocks['euro'] - optimizer._target_reserve_needed.get('euro', 0):,}")

# Test with more euros
rich_stocks = {'euro': 2000000, 'four': 10}
score2 = optimizer.calculate_priority_score(buy_pomme, rich_stocks, 0)
print(f"\nScore at cycle 0 with 2,000,000 euros: {score2:,.2f}")
print(f"Available euros: {rich_stocks['euro'] - optimizer._target_reserve_needed.get('euro', 0):,}")
