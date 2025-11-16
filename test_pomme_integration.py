#!/usr/bin/env python3
"""
Integration test for pomme.krpsim with the UniversalOptimizer.

This script tests the optimizer against the requirements:
1. Final euro output >= 500,000
2. vente_boite executes at least 10 times
3. boite accumulation reaches 100+ units before selling
4. Debug and adjust multipliers/thresholds as needed
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine
from src.data_models import SimulationConfig


def run_pomme_test(max_cycles: int = 50000):
    """
    Run pomme.krpsim simulation and verify requirements.
    
    Args:
        max_cycles: Maximum number of cycles to simulate
        
    Returns:
        Dictionary with test results
    """
    print(f"=" * 80)
    print(f"Running pomme.krpsim integration test with {max_cycles} cycles")
    print(f"=" * 80)
    
    # Load configuration
    config_file = "public/pomme.krpsim"
    config = parse_config_to_simulation(config_file, max_cycles)
    
    print(f"\nConfiguration loaded:")
    print(f"  - Processes: {len(config.processes)}")
    print(f"  - Initial stocks: {len(config.initial_stocks)}")
    print(f"  - Optimization targets: {config.optimization_targets}")
    print(f"  - Max cycles: {max_cycles}")
    
    # Create and run simulation
    print(f"\nStarting simulation...")
    engine = SimulationEngine(config)
    engine.set_performance_monitoring(False)  # Disable for speed
    
    result = engine.run()
    
    print(f"\nSimulation completed!")
    print(f"  - Final cycle: {result.final_cycle}")
    print(f"  - Total executions: {len(result.executions)}")
    print(f"  - Termination reason: {result.termination_reason}")
    
    # Analyze results
    print(f"\n" + "=" * 80)
    print(f"RESULTS ANALYSIS")
    print(f"=" * 80)
    
    # Requirement 1: Final euro output >= 500,000
    final_euro = result.final_stocks.get('euro', 0)
    print(f"\n1. Final euro output: {final_euro:,}")
    req1_pass = final_euro >= 500000
    print(f"   Requirement: >= 500,000")
    print(f"   Status: {'✓ PASS' if req1_pass else '✗ FAIL'}")
    
    # Requirement 2: vente_boite executes at least 10 times
    vente_boite_count = sum(1 for ex in result.executions if ex.process_name == 'vente_boite')
    print(f"\n2. vente_boite executions: {vente_boite_count}")
    req2_pass = vente_boite_count >= 10
    print(f"   Requirement: >= 10")
    print(f"   Status: {'✓ PASS' if req2_pass else '✗ FAIL'}")
    
    # Requirement 3: boite accumulation reaches 100+ units before selling
    # Track boite stock over time
    max_boite_before_first_sale = 0
    boite_stock = 0
    first_vente_boite_cycle = None
    
    for execution in result.executions:
        # Update boite stock based on production
        if 'boite' in execution.resources_produced:
            boite_stock += execution.resources_produced['boite']
        
        # Check if this is vente_boite
        if execution.process_name == 'vente_boite':
            if first_vente_boite_cycle is None:
                first_vente_boite_cycle = execution.start_cycle
                max_boite_before_first_sale = boite_stock
            # Consume boite
            if 'boite' in execution.resources_consumed:
                boite_stock -= execution.resources_consumed['boite']
    
    print(f"\n3. Max boite before first sale: {max_boite_before_first_sale}")
    req3_pass = max_boite_before_first_sale >= 100
    print(f"   Requirement: >= 100")
    print(f"   Status: {'✓ PASS' if req3_pass else '✗ FAIL'}")
    if first_vente_boite_cycle:
        print(f"   First vente_boite at cycle: {first_vente_boite_cycle}")
    
    # Additional analysis
    print(f"\n" + "=" * 80)
    print(f"ADDITIONAL ANALYSIS")
    print(f"=" * 80)
    
    # Show final stocks
    print(f"\nFinal stocks:")
    for resource, quantity in sorted(result.final_stocks.items()):
        if quantity > 0:
            print(f"  {resource}: {quantity:,}")
    
    # Show process execution counts
    print(f"\nProcess execution counts:")
    process_counts = {}
    for execution in result.executions:
        process_counts[execution.process_name] = process_counts.get(execution.process_name, 0) + 1
    
    for process_name, count in sorted(process_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {process_name}: {count}")
    
    # Overall test result
    print(f"\n" + "=" * 80)
    all_pass = req1_pass and req2_pass and req3_pass
    print(f"OVERALL TEST RESULT: {'✓ ALL REQUIREMENTS PASSED' if all_pass else '✗ SOME REQUIREMENTS FAILED'}")
    print(f"=" * 80)
    
    return {
        'final_euro': final_euro,
        'vente_boite_count': vente_boite_count,
        'max_boite_before_first_sale': max_boite_before_first_sale,
        'req1_pass': req1_pass,
        'req2_pass': req2_pass,
        'req3_pass': req3_pass,
        'all_pass': all_pass,
        'final_cycle': result.final_cycle,
        'total_executions': len(result.executions),
        'process_counts': process_counts
    }


if __name__ == "__main__":
    # Allow custom cycle count from command line
    max_cycles = 50000
    if len(sys.argv) > 1:
        max_cycles = int(sys.argv[1])
    
    results = run_pomme_test(max_cycles)
    
    # Exit with appropriate code
    sys.exit(0 if results['all_pass'] else 1)
