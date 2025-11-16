#!/usr/bin/env python3
"""Test scoring for vente processes"""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation
from src.optimizer_new import UniversalOptimizer

# Load config
config = parse_config_to_simulation("public/pomme.krpsim", 10000)

# Create optimizer
optimizer = UniversalOptimizer(
    optimization_targets=config.optimization_targets,
    all_processes=config.processes,
    total_cycles=10000
)

# Find vente processes
vente_tarte_pomme = None
vente_flan = None
for p in config.processes:
    if p.name == "vente_tarte_pomme":
        vente_tarte_pomme = p
    elif p.name == "vente_flan":
        vente_flan = p

# Test stocks at stall point
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

print("Testing vente_tarte_pomme:")
print(f"  Needs: {vente_tarte_pomme.needs}")
print(f"  Results: {vente_tarte_pomme.results}")
score1 = optimizer.calculate_priority_score(vente_tarte_pomme, stall_stocks, 1064)
print(f"  Score at cycle 1064: {score1:,.2f}")

print("\nTesting vente_flan:")
print(f"  Needs: {vente_flan.needs}")
print(f"  Results: {vente_flan.results}")
score2 = optimizer.calculate_priority_score(vente_flan, stall_stocks, 1064)
print(f"  Score at cycle 1064: {score2:,.2f}")

print(f"\nCurrent phase: {optimizer._current_phase}")
print(f"Effective euro reserve: {optimizer._get_effective_reserve('euro', 1064):,}")
