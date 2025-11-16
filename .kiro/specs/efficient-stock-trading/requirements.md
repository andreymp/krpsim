# Requirements Document

## Introduction

This document specifies requirements for implementing an efficient, universal stock trading algorithm for the krpsim optimizer. The current optimizer achieves only ~54K euros on pomme.krpsim (target: 500K+) and produces small outputs across configurations. The new algorithm must maximize resource production and sales through intelligent stock management, bulk execution strategies, and efficient resource flow optimization.

## Glossary

- **Optimizer**: The system component responsible for selecting which processes to execute to maximize target resources
- **Stock Trading**: The strategy of managing resource accumulation, conversion, and sale to maximize target resource output
- **High-Value Process**: A process that produces significant amounts of target resources (e.g., vente_boite produces 55,000 euro)
- **Value Chain**: The complete dependency graph from raw materials to final products
- **Bulk Execution**: Running a process many times consecutively to maximize efficiency
- **Resource Flow**: The movement of resources through the value chain from gathering to final sale
- **Target Resource**: A resource specified in the optimize directive (e.g., euro, benefice)
- **Intermediate Resource**: A non-target resource needed in the value chain
- **Bottleneck**: A resource shortage that prevents execution of higher-value processes
- **Stock Reserve**: Resources set aside to ensure value chain processes can execute
- **Execution Multiplier**: The number of times a process should be executed in bulk

## Requirements

### Requirement 1: Achieve 500K+ Euro Output on pomme.krpsim

**User Story:** As a user running pomme.krpsim for 50,000 cycles, I want the optimizer to produce at least 500,000 euros, so that the system demonstrates effective stock trading.

#### Acceptance Criteria

1. WHEN the Optimizer executes pomme.krpsim for 50,000 cycles, THE Optimizer SHALL produce a final euro stock of at least 500,000
2. WHEN the Optimizer identifies vente_boite as a High-Value Process, THE Optimizer SHALL execute vente_boite at least 10 times during the simulation
3. WHEN the Optimizer accumulates intermediate resources, THE Optimizer SHALL reserve sufficient boite inventory before executing vente_boite
4. WHEN the Optimizer reaches cycle 40,000, THE Optimizer SHALL have accumulated at least 100 boite units for bulk selling

### Requirement 2: Implement Universal Stock Trading Strategy

**User Story:** As a developer, I want the stock trading algorithm to work universally across all configurations, so that no configuration-specific logic is required.

#### Acceptance Criteria

1. THE Optimizer SHALL identify High-Value Processes based on net production ratios without hardcoded resource names
2. WHEN the Optimizer analyzes any configuration, THE Optimizer SHALL calculate optimal Execution Multipliers based on process characteristics
3. THE Optimizer SHALL determine Resource Flow priorities using value chain analysis without configuration-specific rules
4. WHEN the Optimizer selects processes, THE Optimizer SHALL apply the same scoring logic across all configurations

### Requirement 3: Maximize Bulk Execution Efficiency

**User Story:** As a user, I want the optimizer to execute high-value processes in bulk, so that output is maximized through efficient batch processing.

#### Acceptance Criteria

1. WHEN the Optimizer identifies a High-Value Process with net production > 1000, THE Optimizer SHALL calculate an Execution Multiplier of at least 100
2. WHEN the Optimizer accumulates intermediate resources, THE Optimizer SHALL target quantities sufficient for the calculated Execution Multiplier
3. WHEN the Optimizer has sufficient resources for bulk execution, THE Optimizer SHALL execute the High-Value Process multiple times consecutively
4. THE Optimizer SHALL prevent premature consumption of resources needed for bulk execution by applying Stock Reserves

### Requirement 4: Optimize Resource Flow Through Value Chain

**User Story:** As a user, I want resources to flow efficiently from raw materials to final products, so that the value chain operates without bottlenecks.

#### Acceptance Criteria

1. WHEN the Optimizer detects a Bottleneck in the Value Chain, THE Optimizer SHALL prioritize producing the bottleneck resource with urgency score > 10,000
2. THE Optimizer SHALL calculate resource depth in the Value Chain where depth 1 represents direct inputs to High-Value Processes
3. WHEN the Optimizer is in production phase, THE Optimizer SHALL prioritize processes producing resources with depth >= 2
4. WHEN the Optimizer is in conversion phase, THE Optimizer SHALL prioritize processes producing resources with depth == 1

### Requirement 5: Implement Intelligent Stock Reservation

**User Story:** As a user, I want the optimizer to reserve resources for high-value processes, so that low-value processes don't consume critical resources.

#### Acceptance Criteria

1. WHEN the Optimizer analyzes the Value Chain, THE Optimizer SHALL calculate Stock Reserves for each Target Resource based on High-Value Process needs
2. THE Optimizer SHALL apply penalty factor of 10,000,000 WHEN a non-value-chain process attempts to consume reserved Target Resources
3. THE Optimizer SHALL apply penalty factor of 1,000 WHEN a value-chain process attempts to consume reserved Target Resources
4. THE Optimizer SHALL apply penalty factor of 1.0 WHEN a High-Value Process consumes reserved Target Resources

### Requirement 6: Implement Multi-Phase Execution Strategy

**User Story:** As a user, I want the optimizer to progress through distinct phases, so that resources are gathered, produced, converted, and sold in optimal sequence.

#### Acceptance Criteria

1. THE Optimizer SHALL transition from gathering phase to production phase WHEN value chain stock ratio exceeds 0.02 OR cycle count exceeds 500
2. THE Optimizer SHALL transition from production phase to conversion phase WHEN value chain stock ratio exceeds 0.2 OR cycle count exceeds 1,000
3. THE Optimizer SHALL transition from conversion phase to selling phase WHEN any High-Value Process can execute with current stocks
4. WHEN the Optimizer is in gathering phase, THE Optimizer SHALL apply multiplier of 2.0 to resource gathering processes
5. WHEN the Optimizer is in selling phase, THE Optimizer SHALL apply multiplier of 10,000,000 to High-Value Processes

### Requirement 7: Prevent Resource Waste Through Smart Consumption

**User Story:** As a user, I want the optimizer to avoid wasting accumulated resources, so that bulk execution targets are not undermined.

#### Acceptance Criteria

1. WHEN the Optimizer identifies a resource with a bulk target, THE Optimizer SHALL apply penalty factor of 0.0001 to processes that consume that resource
2. THE Optimizer SHALL exempt processes from bulk consumption penalties WHEN current Target Resource stock is below Stock Reserve AND the process produces Target Resources
3. WHEN the Optimizer detects a process consuming bulk-targeted resources, THE Optimizer SHALL check if the process is critical for euro generation before applying penalties
4. THE Optimizer SHALL track bulk targets for resources at depth 1 and depth 2 in the Value Chain

### Requirement 8: Increase Output Across All Configurations

**User Story:** As a user running any configuration, I want the optimizer to produce larger outputs than the current implementation, so that the system demonstrates improved performance universally.

#### Acceptance Criteria

1. WHEN the Optimizer executes simple.krpsim, THE Optimizer SHALL produce output at least equal to the current implementation
2. WHEN the Optimizer executes ikea.krpsim, THE Optimizer SHALL produce output at least 20% higher than the current implementation
3. WHEN the Optimizer executes pirates.krpsim, THE Optimizer SHALL produce output at least 20% higher than the current implementation
4. WHEN the Optimizer executes mtrazzi.krpsim, THE Optimizer SHALL produce output at least 20% higher than the current implementation

### Requirement 9: Implement Adaptive Execution Multipliers

**User Story:** As a developer, I want execution multipliers to adapt based on simulation length and resource availability, so that the optimizer scales appropriately.

#### Acceptance Criteria

1. WHEN the Optimizer calculates Execution Multipliers, THE Optimizer SHALL consider total simulation cycles in the calculation
2. THE Optimizer SHALL increase Execution Multipliers by factor of 2 WHEN simulation cycles exceed 10,000
3. THE Optimizer SHALL increase Execution Multipliers by factor of 5 WHEN simulation cycles exceed 50,000
4. WHEN the Optimizer detects insufficient resources for calculated multiplier, THE Optimizer SHALL execute with available resources rather than waiting indefinitely

### Requirement 10: Optimize for Long Simulations

**User Story:** As a user running long simulations (50K+ cycles), I want the optimizer to scale its strategy appropriately, so that output grows proportionally with available time.

#### Acceptance Criteria

1. WHEN the Optimizer runs a simulation with cycles > 50,000, THE Optimizer SHALL extend gathering phase limit to at least 500 cycles
2. WHEN the Optimizer runs a simulation with cycles > 50,000, THE Optimizer SHALL increase bulk targets by factor of 5
3. THE Optimizer SHALL adjust phase transition thresholds proportionally WHEN simulation cycles exceed 50,000
4. WHEN the Optimizer reaches 80% of total cycles, THE Optimizer SHALL prioritize High-Value Process execution regardless of bulk targets
