#!/usr/bin/env python3
"""Test adaptive bulk multiplier calculation."""
import math

def calculate_multiplier(max_production):
    """Calculate bulk multiplier using logarithmic scale."""
    if max_production <= 1:
        return 2
    elif max_production <= 10:
        return 5
    else:
        multiplier = int(2 * math.log10(max_production))
        return max(2, min(20, multiplier))

# Test various production values
test_values = [1, 5, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000]

print("Production Value → Bulk Multiplier")
print("=" * 40)
for val in test_values:
    mult = calculate_multiplier(val)
    print(f"{val:>10} → {mult:>2}x")
