#!/usr/bin/env python3
"""Test selection at stall point"""

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

# Stall stocks
stall_stocks = {
    'beurre': 1964,
    'blanc_oeuf': 76,
    'boite': 3,
    'citron': 300,
    'euro': 9310,
    'flan': 32,
    'four': 10,
    'jaune_oeuf': 4,
    'lait': 1948,
    'pomme': 340,
    'tarte_citron': 1,
    'tarte_pomme': 75
}

# Get executable processes
executable = [p for p in config.processes if all(stall_stocks.get(r, 0) >= q for r, q in p.needs.items())]

print(f"Executable processes at stall: {len(executable)}")
for p in executable:
    score = optimizer.calculate_priority_score(p, stall_stocks, 1064)
    print(f"  {p.name}: score={score:,.2f}")

# Select best
best = optimizer.select_best_process(executable, stall_stocks, 1064)
print(f"\nBest process selected: {best.name if best else 'None'}")
