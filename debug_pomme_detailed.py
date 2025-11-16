#!/usr/bin/env python3
"""Detailed debug of pomme.krpsim simulation."""

import sys
sys.path.insert(0, '.')

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine


def main():
    config = parse_config_to_simulation('public/pomme.krpsim', 50000)
    engine = SimulationEngine(config)
    result = engine.run()
    
    print(f"Final cycle: {result.final_cycle}")
    print(f"Termination reason: {result.termination_reason}")
    print(f"Total executions: {len(result.executions)}")
    print(f"Final stocks: {result.final_stocks}")
    
    # Check if vente_boite or do_boite were ever executed
    vente_boite_count = sum(1 for e in result.executions if e.process_name == 'vente_boite')
    do_boite_count = sum(1 for e in result.executions if e.process_name == 'do_boite')
    
    print(f"\nvente_boite executions: {vente_boite_count}")
    print(f"do_boite executions: {do_boite_count}")
    
    # Show last 50 executions
    print(f"\nLast 50 executions:")
    for exec in result.executions[-50:]:
        print(f"  {exec.start_cycle}: {exec.process_name}")


if __name__ == '__main__':
    main()
