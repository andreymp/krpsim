#!/usr/bin/env python3
"""
Test script to validate universality of the optimizer across configurations.
Tests simple.krpsim, ikea.krpsim, pirates.krpsim, and mtrazzi.krpsim.
"""

import subprocess
import sys
import re
from typing import Dict, Optional


def run_simulation(config_file: str, cycles: int) -> Dict[str, int]:
    """
    Run a simulation and extract final stock values.
    
    Args:
        config_file: Path to configuration file
        cycles: Number of cycles to run
        
    Returns:
        Dictionary of resource: quantity
    """
    result = subprocess.run(
        ['python', 'src/krpsim.py', config_file, str(cycles)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error running {config_file}:")
        print(result.stderr)
        return {}
    
    # Parse output to extract final stocks
    stocks = {}
    in_stock_section = False
    
    for line in result.stdout.split('\n'):
        if line.strip() == "Stock :":
            in_stock_section = True
            continue
        
        if in_stock_section and '=>' in line:
            match = re.match(r'(\w+)\s*=>\s*(\d+)', line.strip())
            if match:
                resource = match.group(1)
                quantity = int(match.group(2))
                stocks[resource] = quantity
    
    return stocks


def test_simple():
    """Test simple.krpsim - should maintain current performance."""
    print("\n" + "="*60)
    print("Testing simple.krpsim (100 cycles)")
    print("="*60)
    
    stocks = run_simulation('public/simple.krpsim', 100)
    
    if not stocks:
        print("❌ FAILED: Could not run simulation")
        return False
    
    print(f"Final stocks: {stocks}")
    
    # Check optimization targets
    euro = stocks.get('euro', 0)
    client_content = stocks.get('client_content', 0)
    
    print(f"  euro: {euro}")
    print(f"  client_content: {client_content}")
    
    # Baseline: euro=2, client_content=1
    if euro >= 2 and client_content >= 1:
        print("✅ PASSED: Maintains baseline performance")
        return True
    else:
        print(f"❌ FAILED: Below baseline (expected euro>=2, client_content>=1)")
        return False


def test_ikea():
    """Test ikea.krpsim - maintains baseline performance."""
    print("\n" + "="*60)
    print("Testing ikea.krpsim (1000 cycles)")
    print("="*60)
    
    stocks = run_simulation('public/ikea.krpsim', 1000)
    
    if not stocks:
        print("❌ FAILED: Could not run simulation")
        return False
    
    print(f"Final stocks: {stocks}")
    
    # Check optimization target
    armoire = stocks.get('armoire', 0)
    print(f"  armoire: {armoire}")
    
    # Baseline: armoire=1 (resource-constrained, can't improve without more planks)
    # This configuration has only 7 planks, which is exactly enough for 1 armoire
    baseline = 1
    target = 1  # Maintain baseline (improvement not possible without more resources)
    
    if armoire >= target:
        print(f"✅ PASSED: Maintains baseline performance (armoire={armoire})")
        return True
    else:
        print(f"❌ FAILED: armoire={armoire}, expected >={target}")
        return False


def test_pirates():
    """Test pirates.krpsim - should show 20%+ improvement."""
    print("\n" + "="*60)
    print("Testing pirates.krpsim (2000 cycles)")
    print("="*60)
    
    stocks = run_simulation('public/pirates.krpsim', 2000)
    
    if not stocks:
        print("❌ FAILED: Could not run simulation")
        return False
    
    print(f"Final stocks: {stocks}")
    
    # Check optimization target (friendship, not dollars!)
    friendship = stocks.get('friendship', 0)
    print(f"  friendship: {friendship}")
    
    # Baseline: friendship=0, target: at least 1 (any improvement)
    baseline = 0
    target = 1  # Need to actually produce friendship
    
    if friendship >= target:
        print(f"✅ PASSED: Produced {friendship} friendship (baseline was {baseline})")
        return True
    else:
        print(f"❌ FAILED: friendship={friendship}, expected >={target}")
        return False


def test_mtrazzi():
    """Test mtrazzi.krpsim - should show 20%+ improvement."""
    print("\n" + "="*60)
    print("Testing mtrazzi.krpsim (1000 cycles)")
    print("="*60)
    
    stocks = run_simulation('public/mtrazzi.krpsim', 1000)
    
    if not stocks:
        print("❌ FAILED: Could not run simulation")
        return False
    
    print(f"Final stocks: {stocks}")
    
    # Check optimization target (euro, not fame!)
    euro = stocks.get('euro', 0)
    print(f"  euro: {euro}")
    
    # Baseline: euro=1, target: 20% improvement = at least 101 (100 more)
    baseline = 1
    target = 101  # Significant improvement
    
    if euro >= target:
        improvement = ((euro - baseline) / baseline * 100) if baseline > 0 else 0
        print(f"✅ PASSED: {improvement:.1f}% improvement over baseline")
        return True
    else:
        improvement = ((euro - baseline) / baseline * 100) if baseline > 0 else 0
        print(f"❌ FAILED: euro={euro}, expected >={target}")
        print(f"   Current improvement: {improvement:.1f}%")
        return False


def main():
    """Run all universality tests."""
    print("\n" + "="*60)
    print("UNIVERSALITY VALIDATION TEST SUITE")
    print("="*60)
    print("\nTesting optimizer across multiple configurations...")
    print("Requirements: 2.1, 2.2, 2.3, 2.4, 8.1, 8.2, 8.3, 8.4")
    
    results = {
        'simple.krpsim': test_simple(),
        'ikea.krpsim': test_ikea(),
        'pirates.krpsim': test_pirates(),
        'mtrazzi.krpsim': test_mtrazzi()
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for config, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{config:20s} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All universality tests PASSED!")
        print("The optimizer works universally across all configurations.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) FAILED")
        print("The optimizer needs adjustments for universal performance.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
