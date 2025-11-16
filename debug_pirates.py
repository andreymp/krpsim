#!/usr/bin/env python3
"""Debug pirates.krpsim specifically."""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine


def main():
    config = parse_config_to_simulation('public/pirates.krpsim', 1000)
    engine = SimulationEngine(config)
    result = engine.run()
    
    print(f"Final cycle: {result.final_cycle}")
    print(f"Termination reason: {result.termination_reason}")
    print(f"Final stocks: {result.final_stocks}")
    print(f"\nLast 20 executions:")
    for exec in result.executions[-20:]:
        print(f"  {exec.start_cycle}: {exec.process_name}")


if __name__ == '__main__':
    main()
