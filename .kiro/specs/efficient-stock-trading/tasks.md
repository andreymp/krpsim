# Implementation Plan

- [x] 1. Enhance value chain analysis with bulk target calculation
  - Implement recursive bulk target calculation with depth limits and reduction factors
  - Update `_analyze_value_chains()` to call bulk target calculation after dependency tracking
  - Ensure bulk targets use `max()` instead of `sum()` to avoid over-production
  - Calculate bulk targets for high-value process inputs (quantity * 100)
  - Calculate bulk targets for depth-2 resources with 50% reduction factor
  - Limit recursion to max_depth=3 to prevent excessive upstream production
  - _Requirements: 3.1, 3.2, 3.3, 7.1, 7.4_

- [x] 2. Implement resource reservation system
  - Calculate target resource reserves for high-value processes (needs * 100)
  - Calculate target resource reserves for intermediate processes (needs * 500)
  - Use `max()` to avoid over-reservation when multiple processes need same resource
  - Store reserves in `_target_reserve_needed` dictionary
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 3. Implement value chain depth calculation
  - Create `_calculate_value_chain_depth()` method
  - Assign depth 1 to direct inputs of high-value processes
  - Recursively calculate depth for upstream resources (depth + 1)
  - Use iterative approach with max_iterations=10 to handle complex dependencies
  - Store depth values in `_value_chain_depth` dictionary
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 4. Enhance process scoring with bulk execution logic
- [x] 4.1 Add bulk consumption penalty logic
  - Check if process consumes resources in `_bulk_targets`
  - Check if current stock < bulk target for consumed resources
  - Apply penalty factor 0.0001 for bulk consumption
  - Exception: Allow if low on euro AND process produces euro (penalty = 1.0)
  - _Requirements: 3.4, 7.1, 7.2, 7.3_

- [x] 4.2 Add bulk production bonus logic
  - Check if process produces resources in `_bulk_targets`
  - Calculate shortage ratio: (bulk_target - current_stock) / bulk_target
  - Apply multiplier: (1,000.0 + shortage_ratio * 100,000.0) if below target
  - Apply penalty: 0.0001 if above target
  - _Requirements: 3.1, 3.2, 7.1_

- [x] 4.3 Update target consumption penalties with reservation logic
  - Calculate available_stock = current_stock - reserve_needed
  - Apply graduated penalties based on available stock levels
  - High-value processes: penalty_factor = 1.0 (can use reserves)
  - Value chain processes: penalty_factor = 1,000.0 (limited reserve use)
  - Other processes: penalty_factor = 10,000,000.0 (cannot use reserves)
  - _Requirements: 5.2, 5.3, 5.4_

- [x] 5. Implement phase detection and management
- [x] 5.1 Create phase detection logic
  - Implement `_detect_phase()` method with cycle and stock-based transitions
  - Gathering → Production: cycle > 500 OR value_chain_stock > needed * 0.02
  - Production → Conversion: cycle > 1,000 OR value_chain_stock > needed * 0.2
  - Conversion/Production/Gathering → Selling: can_execute_hv = True
  - Force transition out of gathering after `_gathering_limit_cycle`
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 5.2 Add phase-specific multipliers to scoring
  - Gathering phase: Resource gatherers × 2.0
  - Production phase: Depth >= 2 producers × 50.0, gatherers × 0.0001
  - Conversion phase: Depth == 1 producers × 500.0, depth == 2 × 100.0, gatherers × 0.000001
  - Selling phase: High-value processes × 10,000,000, others × 0.01, gatherers × 0.00000001
  - _Requirements: 6.4, 6.5_

- [x] 5.3 Implement long simulation adjustments
  - Detect simulations with cycles > 50,000
  - Extend `_gathering_limit_cycle` to 500 for long simulations
  - Increase bulk targets by factor of 5 for long simulations
  - Adjust phase transition thresholds proportionally
  - Force selling phase at 80% of total cycles
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 6. Enhance bottleneck detection with bulk awareness
- [x] 6.1 Update bottleneck detection to use bulk targets
  - Check value chain resources against bulk targets (not just stock < 10)
  - Calculate urgency = (bulk_target - current_stock) * 1,000.0
  - Fallback to absolute threshold (stock < 10) if no bulk target
  - _Requirements: 4.1, 7.1_

- [x] 6.2 Add blocking resource tracking for high-value processes
  - Track resources preventing high-value process execution
  - Store blocking resources with (needed, have) tuples
  - Check both single execution and bulk execution (quantity * 100)
  - _Requirements: 3.2, 4.1_

- [x] 6.3 Implement phase-specific blocking resolution
  - In conversion/selling phases, detect if HV processes are blocked
  - Force production of blocking resources with priority = 10,000,000.0 + urgency
  - Calculate urgency = (needed - have) * 10,000.0 for blocking resources
  - _Requirements: 4.1, 6.3, 6.4_

- [x] 7. Update process selection logic
- [x] 7.1 Enhance high-value process boost logic
  - Check if HV process can execute (has all intermediate resources)
  - Check if HV process can execute in bulk (has resources for 100x)
  - Apply 10,000,000x boost in conversion/selling phases if can execute
  - Apply 1,000,000x boost in other phases if can execute
  - Apply 100x boost if can execute once but not in bulk
  - _Requirements: 1.2, 1.3, 3.1, 3.2_

- [x] 7.2 Add value chain resource boost logic
  - Check if process produces resources needed by high-value processes
  - Calculate total_needed = quantity * 100 for bulk requirements
  - Apply boost_factor = 100.0 + min(shortage / 10.0, 1,000.0) if below target
  - Mark process as producing critical resource for sorting
  - _Requirements: 3.2, 4.3, 4.4_

- [x] 7.3 Implement critical resource sorting
  - Sort processes by (produces_critical_resource, -depth, score)
  - Prioritize processes producing critical resources first
  - Prioritize lower depth (closer to high-value) second
  - Prioritize higher score third
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 8. Add adaptive execution multipliers
  - Calculate execution multipliers based on simulation length
  - Increase multipliers by 2x for simulations > 10,000 cycles
  - Increase multipliers by 5x for simulations > 50,000 cycles
  - Apply multipliers to bulk targets and resource reserves
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 9. Integrate and test with pomme.krpsim
  - Run optimizer with pomme.krpsim for 50,000 cycles
  - Verify vente_boite executes at least 10 times
  - Verify boite accumulation reaches 100+ units before selling
  - Verify final euro output >= 500,000
  - Debug and adjust multipliers/thresholds as needed
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 10. Validate universality across configurations
  - Test with simple.krpsim and verify output >= current implementation
  - Test with ikea.krpsim and verify output >= 20% improvement
  - Test with pirates.krpsim and verify output >= 20% improvement
  - Test with mtrazzi.krpsim and verify output >= 20% improvement
  - Verify no configuration-specific logic is required
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 8.1, 8.2, 8.3, 8.4_
