#!/usr/bin/env python3
"""Debug why simulation stalls"""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine

# Load config
config = parse_config_to_simulation("public/pomme.krpsim", 10000)

# Create engine
engine = SimulationEngine(config)
engine.set_performance_monitoring(False)

# Run simulation
result = engine.run()

print(f"Simulation ended at cycle: {result.final_cycle}")
print(f"Termination reason: '{result.termination_reason}'")
print(f"Total executions: {len(result.executions)}")

# Check final stocks
print(f"\nFinal stocks:")
for resource, qty in sorted(result.final_stocks.items()):
    if qty > 0:
        print(f"  {resource}: {qty}")

# Check what processes could execute at the end
print(f"\nProcesses that could execute with final stocks:")
for process in config.processes:
    can_execute = all(
        result.final_stocks.get(r, 0) >= q 
        for r, q in process.needs.items()
    )
    if can_execute:
        print(f"  {process.name}: needs {process.needs}, produces {process.results}")
