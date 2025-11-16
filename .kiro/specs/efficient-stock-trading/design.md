# Design Document: Efficient Stock Trading Algorithm

## Overview

This design document specifies a universal, efficient stock trading algorithm for the krpsim optimizer that maximizes resource production through intelligent value chain analysis, bulk execution strategies, and multi-phase optimization. The algorithm must work universally across all configurations without hardcoded logic, achieving 500K+ euros on pomme.krpsim (50K cycles) while improving performance across all test cases.

### Core Design Principles

1. **Universal Analysis**: Identify high-value processes and value chains through algorithmic analysis, not configuration-specific rules
2. **Bulk Execution**: Accumulate resources for bulk execution of high-value processes (100x multiplier)
3. **Phase-Based Strategy**: Progress through gathering → production → conversion → selling phases
4. **Smart Reservation**: Reserve target resources for value chain processes to prevent waste
5. **Bottleneck Resolution**: Detect and resolve resource bottlenecks with urgency-based prioritization

## Architecture

### Component Structure

```
UniversalOptimizer
├── Value Chain Analyzer
│   ├── High-Value Process Detector
│   ├── Dependency Tracker
│   ├── Depth Calculator
│   └── Bulk Target Calculator
├── Phase Manager
│   ├── Phase Detector
│   ├── Transition Controller
│   └── Phase-Specific Multipliers
├── Scoring Engine
│   ├── Base Score Calculator
│   ├── Target Production Bonuses
│   ├── Reservation Penalties
│   ├── Bulk Execution Modifiers
│   └── Phase-Based Adjustments
└── Process Selector
    ├── Bottleneck Detector
    ├── Blocking Resource Tracker
    └── Priority Scorer
```

### Data Flow

1. **Initialization**: Receive all processes upfront for complete value chain analysis
2. **Analysis Phase**: Identify high-value processes, build dependency graph, calculate bulk targets
3. **Selection Loop**: For each cycle, detect phase → check bottlenecks → score processes → select best
4. **Execution**: Return selected process to simulation engine

## Components and Interfaces

### 1. Value Chain Analyzer

**Purpose**: Identify high-value processes and their complete dependency chains

**Key Methods**:
- `_analyze_value_chains(all_processes)`: Main analysis entry point
- `_track_dependencies_recursive(process, all_processes, visited)`: Build dependency graph
- `_calculate_value_chain_depth(all_processes)`: Assign depth values to resources
- `_calculate_bulk_targets_recursive(all_processes, depth, max_depth)`: Calculate bulk production targets

**High-Value Process Detection Criteria**:
```python
is_high_value = (
    net_production > 1000 OR
    (consumption > 0 AND net_production > 50 * consumption) OR
    production > 10000
)
```

**Value Chain Depth**:
- Depth 0: High-value processes themselves
- Depth 1: Direct inputs to high-value processes (e.g., boite for vente_boite)
- Depth 2: Inputs to depth-1 resources (e.g., tarte_pomme for do_boite)
- Depth 3+: Further upstream resources

**Bulk Target Calculation**:
- High-value process inputs: `quantity * 100` (for 100x bulk execution)
- Depth-2 resources: Calculate based on production ratios with 50% reduction factor
- Depth-3 resources: Further reduced by 50% per level (max depth 3)

**Resource Reservation**:
- High-value processes: Reserve `needs[target] * 100`
- Intermediate processes: Reserve `needs[target] * 500`
- Use `max()` instead of `sum()` to avoid over-reservation

### 2. Phase Manager

**Purpose**: Detect and manage optimization phases

**Phases**:
1. **Gathering** (cycles 0-500): Acquire raw materials and build initial stocks
2. **Production** (cycles 500-1000): Produce intermediate resources (depth >= 2)
3. **Conversion** (cycles 1000+): Convert to direct high-value inputs (depth == 1)
4. **Selling** (when ready): Execute high-value processes in bulk

**Transition Logic**:
```python
if can_execute_hv:
    return "selling"
elif cycle > 1000 OR value_chain_stock > needed * 0.2:
    return "conversion"
elif cycle > 500 OR value_chain_stock > needed * 0.02:
    return "production"
else:
    return "gathering"
```

**Long Simulation Adjustments** (cycles > 50K):
- Extend gathering limit to 500 cycles
- Increase bulk targets by 5x
- Adjust phase transition thresholds proportionally
- At 80% of total cycles, force selling phase

**Phase-Specific Multipliers**:
- Gathering: Resource gatherers × 2.0
- Production: Depth >= 2 producers × 50.0, gatherers × 0.0001
- Conversion: Depth == 1 producers × 500.0, depth == 2 × 100.0, gatherers × 0.000001
- Selling: High-value processes × 10,000,000, others × 0.01, gatherers × 0.00000001

### 3. Scoring Engine

**Purpose**: Calculate priority scores for process selection

**Base Score Calculation**:
```python
if no_needs:
    base_score = 100,000.0
elif input_cost > 0:
    efficiency = output_value / input_cost
    base_score = efficiency * 100.0
else:
    base_score = output_value * 100.0
```

**Target Production Bonuses**:
```python
bonus = net_production * 50,000.0
if net_production > 10,000: bonus *= 200.0
elif net_production > 1,000: bonus *= 80.0
elif net_production > 100: bonus *= 30.0
elif net_production > 0: bonus *= 10.0
```

**Bulk Consumption Penalties**:
- If process consumes bulk-targeted resource AND current_stock < bulk_target:
  - Exception: Low on euro AND process produces euro → penalty = 1.0
  - Otherwise: penalty = 0.0001 (massive penalty)

**Target Consumption Penalties**:
```python
available_stock = current_stock - reserve_needed
if available_stock < consumption:
    if high_value_process: penalty_factor = 1.0
    elif value_chain_process: penalty_factor = 1,000.0
    else: penalty_factor = 10,000,000.0
else:
    # Graduated penalties based on available stock
    if available_stock < 100: penalty_factor = 10,000.0
    elif available_stock < 1,000: penalty_factor = 1,000.0
    elif available_stock < 10,000: penalty_factor = 100.0
    else: penalty_factor = 10.0
```

**Bulk Production Bonuses**:
```python
if current_stock < bulk_target:
    shortage_ratio = (bulk_target - current_stock) / bulk_target
    score *= (1,000.0 + shortage_ratio * 100,000.0)
else:
    score *= 0.0001  # Heavy penalty if above target
```

### 4. Process Selector

**Purpose**: Select the best process considering bottlenecks and priorities

**Bottleneck Detection Strategy**:

1. **Value Chain Bottlenecks**: Resources in value chain with stock < bulk_target
   - Urgency = `(bulk_target - current_stock) * 1,000.0`
   - Priority = `downstream_value + urgency`

2. **High-Value Process Blockers**: Resources preventing HV execution
   - Base value = 1,000,000.0 for HV processes, 500,000.0 for intermediates
   - Urgency = `(quantity * multiplier - current_stock) * 1,000.0`

3. **Phase-Specific Blocking** (conversion/selling phases):
   - If HV process blocked, force production with priority = `10,000,000.0 + urgency`

**Selection Algorithm**:
```python
1. Check for bottlenecks → return highest urgency producer
2. Score all available processes
3. Apply high-value process boosts (1,000,000x - 10,000,000x)
4. Apply phase-based multipliers
5. Apply value chain resource boosts
6. Sort by (produces_critical, -depth, score)
7. Return highest scoring process if score > 0
```

## Data Models

### Core State Variables

```python
# Configuration
_optimization_targets: List[str]  # e.g., ["euro"]
_stock_targets: List[str]  # Targets excluding "time"
_time_optimization_enabled: bool

# Value Chain Analysis
_high_value_processes: Set[str]  # Process names
_value_chain_resources: Set[str]  # Resource names
_intermediate_needs: Dict[str, Dict[str, int]]  # {process_name: {resource: qty}}
_value_chain_depth: Dict[str, int]  # {resource: depth}
_bulk_targets: Dict[str, int]  # {resource: target_quantity}
_target_reserve_needed: Dict[str, int]  # {target_resource: reserved_qty}

# Phase Management
_current_phase: str  # "gathering", "production", "conversion", "selling"
_phase_transition_cycle: int
_gathering_limit_cycle: int  # Default 300, scales with simulation length

# Analysis State
_analyzed: bool
_all_processes: List[Process]
```

### Process Interface

```python
class Process:
    name: str
    needs: Dict[str, int]  # {resource: quantity}
    results: Dict[str, int]  # {resource: quantity}
    delay: int
    execution_count: int  # Tracked by simulation engine
```

## Error Handling

### Analysis Errors

**Empty Process List**:
- Behavior: Skip analysis, operate in degraded mode
- Fallback: Use base scoring without value chain analysis

**Circular Dependencies**:
- Prevention: Use `visited` set in recursive dependency tracking
- Behavior: Stop recursion when resource already visited

**Missing High-Value Processes**:
- Detection: `len(_high_value_processes) == 0` after analysis
- Behavior: All processes scored equally, no phase transitions

### Runtime Errors

**No Available Processes**:
- Return: `None` from `select_best_process()`
- Simulation: Will wait or terminate based on engine logic

**All Scores Negative**:
- Return: `None` (no good options)
- Cause: All processes consume reserved resources or bulk targets

**Division by Zero**:
- Context: Efficiency calculation when `input_cost == 0`
- Handling: Use `output_value * 100.0` as base score

### Resource Errors

**Insufficient Reserves**:
- Detection: `available_stock < consumption`
- Behavior: Apply heavy penalty (10,000,000x for non-value-chain)
- Result: Process deprioritized but not blocked

**Bulk Target Conflicts**:
- Scenario: Multiple processes need same bulk resource
- Resolution: Use `max()` for bulk targets, not `sum()`
- Behavior: Prioritize by urgency (shortage * 1,000.0)

## Testing Strategy

### Unit Testing

**Value Chain Analysis Tests**:
- Test high-value process detection with various net production values
- Test dependency tracking with linear and branching chains
- Test depth calculation with multi-level dependencies
- Test bulk target calculation with reduction factors
- Test resource reservation with multiple value chain processes

**Phase Detection Tests**:
- Test phase transitions based on cycle counts
- Test phase transitions based on stock ratios
- Test long simulation adjustments (50K+ cycles)
- Test forced selling phase at 80% completion

**Scoring Tests**:
- Test base score calculation with various efficiency ratios
- Test target production bonuses with different net production values
- Test bulk consumption penalties with/without euro shortage
- Test target consumption penalties with different stock levels
- Test phase-based multipliers for each phase

**Bottleneck Detection Tests**:
- Test value chain bottleneck detection with bulk targets
- Test high-value process blocker detection
- Test phase-specific blocking in conversion/selling phases
- Test urgency calculation and prioritization

### Integration Testing

**End-to-End Simulation Tests**:
- Test pomme.krpsim achieving 500K+ euros (50K cycles)
- Test simple.krpsim maintaining current performance
- Test ikea.krpsim with 20%+ improvement
- Test pirates.krpsim with 20%+ improvement
- Test mtrazzi.krpsim with 20%+ improvement

**Phase Progression Tests**:
- Verify gathering phase accumulates raw materials
- Verify production phase builds intermediate resources
- Verify conversion phase produces direct HV inputs
- Verify selling phase executes high-value processes in bulk

**Bulk Execution Tests**:
- Verify boite accumulation to 100+ units before vente_boite
- Verify bulk targets prevent premature consumption
- Verify high-value processes execute multiple times consecutively

### Performance Testing

**Scalability Tests**:
- Test with 10K, 50K, 100K cycle simulations
- Verify phase adjustments scale appropriately
- Verify bulk targets scale with simulation length

**Universality Tests**:
- Test with configurations having different target resources
- Test with configurations having different value chain depths
- Test with configurations having multiple high-value processes
- Verify no configuration-specific logic required

## Implementation Notes

### Critical Implementation Details

1. **Upfront Analysis**: All processes must be provided at initialization for complete value chain analysis
2. **Bulk Target Recursion**: Limit to max_depth=3 with 50% reduction per level to avoid over-production
3. **Resource Reservation**: Use `max()` not `sum()` to avoid over-reserving when multiple processes need same resource
4. **Phase Transitions**: Check phase on every cycle, allow transitions in both directions if needed
5. **Bottleneck Priority**: Always return bottleneck producer before scoring other processes
6. **Score Sorting**: Sort by (critical_resource, -depth, score) to prioritize value chain building

### Performance Optimizations

1. **Single Analysis Pass**: Analyze value chains once at initialization, not per cycle
2. **Cached Depth Values**: Calculate resource depths once, reuse in scoring
3. **Early Returns**: Return bottleneck producers immediately without scoring all processes
4. **Efficient Sorting**: Use tuple sorting instead of multiple sort passes

### Known Limitations

1. **Static Analysis**: Cannot adapt to dynamic process additions (requires re-initialization)
2. **Fixed Multipliers**: Bulk multiplier (100x) is hardcoded, not adaptive to simulation length
3. **Phase Rigidity**: Phase transitions based on fixed thresholds, not adaptive to configuration
4. **Memory Usage**: Stores all processes in memory for analysis (O(n) space)

### Future Enhancements

1. **Adaptive Multipliers**: Calculate bulk multipliers based on simulation length and process characteristics
2. **Dynamic Re-Analysis**: Trigger re-analysis when new processes become available
3. **Multi-Target Optimization**: Better handling of multiple optimization targets simultaneously
4. **Learning-Based Adjustments**: Track execution outcomes and adjust strategies dynamically
