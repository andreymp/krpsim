#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine

config = parse_config_to_simulation('public/pomme.krpsim', 50000)
engine = SimulationEngine(config)
result = engine.run()

print(f"Final cycle: {result.final_cycle}")
print(f"Final euro: {result.final_stocks.get('euro', 0)}")
print(f"Final stocks: {result.final_stocks}")
print(f"Total executions: {len(result.executions)}")

# Count process types
from collections import Counter
process_counts = Counter(e.process_name for e in result.executions)
print(f"\nTop 10 processes:")
for name, count in process_counts.most_common(10):
    print(f"  {name}: {count}")
