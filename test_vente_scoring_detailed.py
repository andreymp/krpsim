#!/usr/bin/env python3
"""Detailed scoring test for vente processes"""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation, Process
from src.optimizer_new import UniversalOptimizer

# Load config
config = parse_config_to_simulation("public/pomme.krpsim", 10000)

# Create optimizer
optimizer = UniversalOptimizer(
    optimization_targets=config.optimization_targets,
    all_processes=config.processes,
    total_cycles=10000
)

# Find vente_tarte_pomme
vente_tarte_pomme = None
for p in config.processes:
    if p.name == "vente_tarte_pomme":
        vente_tarte_pomme = p
        break

# Test stocks
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

print("Manual scoring calculation for vente_tarte_pomme:")
print(f"  Needs: {vente_tarte_pomme.needs}")
print(f"  Results: {vente_tarte_pomme.results}")
print(f"  Delay: {vente_tarte_pomme.delay}")

# Calculate input cost and output value
input_cost = sum(vente_tarte_pomme.needs.values())
output_value = sum(vente_tarte_pomme.results.values())
print(f"\n  input_cost: {input_cost}")
print(f"  output_value: {output_value}")

# Base score
if len(vente_tarte_pomme.needs) == 0:
    base_score = 100000.0
elif input_cost > 0:
    efficiency = output_value / input_cost
    base_score = efficiency * 100.0
else:
    base_score = output_value * 100.0

print(f"  efficiency: {output_value / input_cost if input_cost > 0 else 'N/A'}")
print(f"  base_score: {base_score}")

# Target production bonus
net_euro = vente_tarte_pomme.results.get('euro', 0) - vente_tarte_pomme.needs.get('euro', 0)
print(f"\n  net_euro: {net_euro}")

bonus = net_euro * 50000.0
if net_euro > 10000:
    bonus *= 200.0
elif net_euro > 1000:
    bonus *= 80.0
elif net_euro > 100:
    bonus *= 30.0
elif net_euro > 0:
    bonus *= 10.0

print(f"  target production bonus: {bonus}")

score = base_score + bonus
print(f"  score after bonus: {score}")

# Delay penalty
score -= vente_tarte_pomme.delay * 1.0
print(f"  score after delay penalty: {score}")

# Execution count penalty
score -= vente_tarte_pomme.execution_count * 0.1
print(f"  score after execution count penalty: {score}")

print(f"\n  Final manual score: {score}")

# Compare with actual
actual_score = optimizer.calculate_priority_score(vente_tarte_pomme, stall_stocks, 1064)
print(f"  Actual optimizer score: {actual_score}")
