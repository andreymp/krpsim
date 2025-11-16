from typing import Dict, List, Optional, Set
from src.common import Process


class UniversalOptimizer:
    """Universal optimizer that works for any configuration."""
    
    def __init__(self, optimization_targets: List[str], all_processes: Optional[List[Process]] = None, total_cycles: int = 0):
        """
        Initialize optimizer with targets and optionally all processes.
        
        Args:
            optimization_targets: List of resources to optimize (or "time")
            all_processes: Optional list of all processes for upfront analysis
            total_cycles: Total number of cycles for the simulation (0 if unknown)
        """
        # Configuration
        self._optimization_targets = optimization_targets.copy()
        self._stock_targets = [t for t in optimization_targets if t != 'time']
        self._time_optimization_enabled = 'time' in optimization_targets
        self._total_cycles = total_cycles
        
        # Value chain analysis state
        self._high_value_processes: Set[str] = set()
        self._value_chain_resources: Set[str] = set()
        self._intermediate_needs: Dict[str, Dict[str, int]] = {}
        self._analyzed = False
        self._all_processes: List[Process] = all_processes if all_processes else []
        self._target_reserve_needed: Dict[str, int] = {}  # Track how much of target resources to reserve
        
        # Phase detection state
        self._current_phase: str = "gathering"  # gathering, production, conversion, selling
        self._phase_transition_cycle: int = 0
        self._resource_budget: Dict[str, int] = {}  # Budget for each target resource
        self._value_chain_depth: Dict[str, int] = {}  # Depth of each resource in value chain
        self._gathering_limit_cycle: int = 300  # Stop gathering after this many cycles
        self._bulk_targets: Dict[str, int] = {}  # Resources that need bulk production (resource -> target amount)
        
        # Cash-flow mode state (prevents stalls)
        self._stuck_counter: int = 0  # Count cycles with no positive scores
        self._cash_flow_mode: bool = False  # Emergency mode to restart production
        self._last_selection_cycle: int = 0  # Track last successful selection
        
        # Calculate adaptive execution multiplier based on simulation length
        self._execution_multiplier = self._calculate_execution_multiplier(total_cycles)
        
        # Detect long simulations and adjust parameters
        self._is_long_simulation = total_cycles > 50000
        if self._is_long_simulation:
            # Extend gathering limit to 500 for long simulations
            self._gathering_limit_cycle = 500
        
        # Perform upfront analysis if all processes provided
        if self._all_processes:
            self._analyze_value_chains(self._all_processes)
    
    def _calculate_execution_multiplier(self, total_cycles: int) -> float:
        """
        Calculate adaptive execution multiplier based on simulation length.
        
        Args:
            total_cycles: Total number of cycles for the simulation
            
        Returns:
            Execution multiplier (1.0 for short, 2.0 for medium, 5.0 for long simulations)
        """
        if total_cycles > 50000:
            # Increase multipliers by 5x for simulations > 50,000 cycles
            return 5.0
        elif total_cycles > 10000:
            # Increase multipliers by 2x for simulations > 10,000 cycles
            return 2.0
        else:
            # Default multiplier for short simulations
            return 1.0
    
    def _calculate_adaptive_bulk_multiplier(self, all_processes: List[Process]) -> int:
        """
        Calculate adaptive bulk multiplier based on configuration scale.
        
        For large-scale configs with high production values, use larger multipliers.
        For small-scale configs with low production values, use smaller multipliers.
        
        Args:
            all_processes: List of all available processes
            
        Returns:
            Bulk multiplier (typically between 2 and 50)
        """
        # Find the maximum production value across all high-value processes
        max_production = 0
        for hv_process_name in self._high_value_processes:
            for process in all_processes:
                if process.name == hv_process_name:
                    for target in self._stock_targets:
                        if target in process.results:
                            production = process.results[target]
                            max_production = max(max_production, production)
        
        # Scale bulk multiplier based on production values
        # Use more conservative multipliers to allow progressive accumulation
        if max_production >= 10000:
            # Large-scale config (e.g., pomme with 55,000 euro production)
            # Use 20x instead of 100x for more achievable targets
            return 20
        elif max_production >= 1000:
            # Medium-scale config
            return 10
        elif max_production >= 100:
            # Small-scale config
            return 5
        else:
            # Very small-scale config (e.g., ikea with 1 armoire production)
            return 2
    
    def _analyze_value_chains(self, all_processes: List[Process]) -> None:
        """
        Identify high-value processes and their complete dependency chains.
        
        High-value processes are those that produce significant amounts of target resources.
        This method also tracks all intermediate resources needed in the value chain.
        """
        # Early return if already analyzed or no stock targets
        if self._analyzed or not self._stock_targets:
            return
        
        # First pass: Find maximum net production for each target resource
        max_net_production: Dict[str, float] = {}
        for target in self._stock_targets:
            max_net_production[target] = 0.0
            for process in all_processes:
                if target in process.results:
                    production = process.results[target]
                    consumption = process.needs.get(target, 0)
                    net_production = production - consumption
                    if net_production > max_net_production[target]:
                        max_net_production[target] = net_production
        
        # Second pass: Identify high-value processes using adaptive criteria
        for process in all_processes:
            for target in self._stock_targets:
                if target in process.results:
                    production = process.results[target]
                    consumption = process.needs.get(target, 0)
                    net_production = production - consumption
                    
                    # Adaptive high-value criteria:
                    # 1. Absolute thresholds (for large-scale configs like pomme)
                    # 2. Relative threshold: produces at least 50% of max net production
                    # 3. Best producer: produces the maximum for this target
                    max_for_target = max_net_production.get(target, 0)
                    is_high_value = (
                        net_production > 1000 or
                        (consumption > 0 and net_production > 50 * consumption) or
                        production > 10000 or
                        (max_for_target > 0 and net_production >= max_for_target * 0.5) or
                        (net_production > 0 and net_production == max_for_target)
                    )
                    
                    if is_high_value:
                        # Store high-value process name
                        self._high_value_processes.add(process.name)
                        
                        # Store intermediate needs (non-target resources)
                        for resource, quantity in process.needs.items():
                            if resource not in self._stock_targets:
                                if process.name not in self._intermediate_needs:
                                    self._intermediate_needs[process.name] = {}
                                self._intermediate_needs[process.name][resource] = quantity
                        
                        break  # Process is high-value, no need to check other targets
        
        # Track dependencies for each high-value process
        for process in all_processes:
            if process.name in self._high_value_processes:
                visited: Set[str] = set()
                self._track_dependencies_recursive(process, all_processes, visited)
        
        # Also identify ALL processes that produce value chain resources
        # These are intermediate producers that enable high-value processes
        for process in all_processes:
            produces_value_chain_resource = False
            for resource in process.results:
                if resource in self._value_chain_resources:
                    produces_value_chain_resource = True
                    break
            
            if produces_value_chain_resource and process.name not in self._high_value_processes:
                # This process is part of the value chain
                # Track its needs (non-target resources) as important
                if process.name not in self._intermediate_needs:
                    self._intermediate_needs[process.name] = {}
                
                for resource, quantity in process.needs.items():
                    if resource not in self._stock_targets:
                        self._intermediate_needs[process.name][resource] = quantity
        
        # Calculate how much of target resources need to be reserved for high-value processes
        # and calculate value chain depth for each resource
        self._calculate_value_chain_depth(all_processes)
        
        # Calculate bulk production targets using recursive method with depth limits
        self._calculate_bulk_targets_recursive(all_processes, depth=0, max_depth=3)
        
        # Reserve target resources for ALL value chain processes (not just high-value)
        # Calculate reserves based on bulk targets for intermediate processes
        for process in all_processes:
            # Check if this process is in the value chain
            is_in_value_chain = (
                process.name in self._high_value_processes or
                process.name in self._intermediate_needs
            )
            
            if is_in_value_chain:
                for target in self._stock_targets:
                    if target in process.needs:
                        # This value chain process needs target resources
                        # Calculate minimum reserve needed based on bulk targets
                        
                        if process.name in self._high_value_processes:
                            # Reserve for 100 executions of HV process
                            multiplier = 100
                        else:
                            # For intermediate processes, calculate based on bulk targets
                            # Find what this process produces
                            max_bulk_needed = 0
                            for result_resource in process.results:
                                if result_resource in self._bulk_targets:
                                    bulk_target = self._bulk_targets[result_resource]
                                    production_per_run = process.results[result_resource]
                                    runs_needed = (bulk_target + production_per_run - 1) // production_per_run
                                    max_bulk_needed = max(max_bulk_needed, runs_needed)
                            
                            # Use bulk-based multiplier if available, otherwise use default
                            if max_bulk_needed > 0:
                                multiplier = max_bulk_needed
                            else:
                                multiplier = 500  # Default for intermediate processes
                        
                        # Apply adaptive execution multiplier to resource reserves
                        needed = int(process.needs[target] * multiplier * self._execution_multiplier)
                        if target not in self._target_reserve_needed:
                            self._target_reserve_needed[target] = needed
                        else:
                            # Use max instead of sum to avoid over-reserving
                            self._target_reserve_needed[target] = max(self._target_reserve_needed[target], needed)
        
        # Mark analysis as complete
        self._analyzed = True
    
    def _calculate_bulk_targets_recursive(self, all_processes: List[Process], depth: int = 0, max_depth: int = 3) -> None:
        """
        Recursively calculate bulk production targets for the entire value chain.
        
        Args:
            all_processes: List of all available processes
            depth: Current recursion depth (0 = high-value process inputs, 1 = depth-1 resources, etc.)
            max_depth: Maximum recursion depth to prevent excessive upstream production
        """
        # Limit recursion to max_depth=3 to prevent excessive upstream production
        if depth >= max_depth:
            return
        
        # Depth 0: Calculate bulk targets for high-value process inputs
        if depth == 0:
            # Calculate adaptive bulk multiplier based on configuration scale
            # For large-scale configs (pomme), use 100x
            # For small-scale configs (ikea, pirates), use smaller multipliers
            bulk_multiplier = self._calculate_adaptive_bulk_multiplier(all_processes)
            
            for hv_process_name in self._high_value_processes:
                for process in all_processes:
                    if process.name == hv_process_name:
                        for resource, quantity in process.needs.items():
                            if resource not in self._stock_targets:
                                # This resource is needed in bulk for HV process
                                bulk_amount = quantity * bulk_multiplier
                                # Note: Don't apply execution multiplier here - bulk_multiplier is already adaptive
                                if resource not in self._bulk_targets:
                                    self._bulk_targets[resource] = bulk_amount
                                else:
                                    # Use max() instead of sum() to avoid over-production
                                    self._bulk_targets[resource] = max(self._bulk_targets[resource], bulk_amount)
                        break
            
            # Recurse to calculate depth-1, depth-2, and depth-3 resources
            self._calculate_bulk_targets_recursive(all_processes, depth + 1, max_depth)
        else:
            # Depth 1+: Calculate bulk targets for upstream resources
            # Get snapshot of current bulk targets to avoid modifying dict during iteration
            resources_to_process = list(self._bulk_targets.keys())
            
            for resource in resources_to_process:
                bulk_amount = self._bulk_targets[resource]
                
                # Find all processes that produce this resource
                for producer in all_processes:
                    if resource in producer.results:
                        # How many times do we need to run this producer?
                        production_per_run = producer.results[resource]
                        runs_needed = (bulk_amount + production_per_run - 1) // production_per_run
                        
                        # What does this producer need?
                        for producer_need, producer_need_qty in producer.needs.items():
                            if producer_need not in self._stock_targets:
                                # Apply 50% reduction factor starting at depth 2 (depth-2 resources)
                                # Depth 1 (depth-1 resources): no reduction (1.0)
                                # Depth 2 (depth-2 resources): 50% reduction (0.5)
                                # Depth 3 (depth-3 resources): 25% reduction (0.25)
                                if depth == 1:
                                    reduction_factor = 1.0  # No reduction for depth-1 resources
                                else:
                                    reduction_factor = 0.5 ** (depth - 1)  # 50% reduction per level starting at depth 2
                                
                                total_needed = int(producer_need_qty * runs_needed * reduction_factor)
                                
                                if total_needed > 0:
                                    if producer_need not in self._bulk_targets:
                                        self._bulk_targets[producer_need] = total_needed
                                    else:
                                        # Use max() instead of sum() to avoid over-production
                                        self._bulk_targets[producer_need] = max(self._bulk_targets[producer_need], total_needed)
            
            # Recurse to handle dependencies of dependencies
            if depth < max_depth - 1:
                self._calculate_bulk_targets_recursive(all_processes, depth + 1, max_depth)
    
    def _calculate_value_chain_depth(self, all_processes: List[Process]) -> None:
        """
        Calculate the depth of each resource in the value chain.
        
        Depth 1: Direct inputs to high-value processes
        Depth 2: Inputs to depth-1 resources (upstream)
        Depth 3+: Further upstream resources
        
        Uses iterative approach with max_iterations=10 to handle complex dependencies.
        We use minimum depth (shortest path) to avoid issues with circular dependencies.
        """
        # Assign depth 1 to direct inputs of high-value processes
        for hv_process_name in self._high_value_processes:
            for process in all_processes:
                if process.name == hv_process_name:
                    for resource in process.needs:
                        if resource not in self._stock_targets:
                            # Direct input to high-value process = depth 1
                            if resource not in self._value_chain_depth:
                                self._value_chain_depth[resource] = 1
                            else:
                                # Keep minimum depth (shortest path to HV process)
                                self._value_chain_depth[resource] = min(
                                    self._value_chain_depth[resource], 1
                                )
        
        # Recursively calculate depth for upstream resources (depth + 1)
        # Use iterative approach with max_iterations=10 to handle complex dependencies
        changed = True
        max_iterations = 10
        iteration = 0
        
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            
            # For each process, if it produces a resource with known depth,
            # then its inputs should have depth + 1 (they are upstream)
            for process in all_processes:
                for result_resource in process.results:
                    # Check if this result has a known depth
                    if result_resource in self._value_chain_depth:
                        result_depth = self._value_chain_depth[result_resource]
                        
                        # All inputs to this process are one level deeper (upstream)
                        for need_resource in process.needs:
                            if need_resource not in self._stock_targets:
                                new_depth = result_depth + 1
                                
                                # Update depth if not set, or keep minimum (shortest path)
                                if need_resource not in self._value_chain_depth:
                                    self._value_chain_depth[need_resource] = new_depth
                                    changed = True
                                # Note: We don't update if new_depth is larger
                                # This keeps the minimum depth (shortest path to HV)
    
    def _track_dependencies_recursive(self, process: Process, all_processes: List[Process], visited: Set[str]) -> None:
        """
        Recursively map complete value chains from raw materials to end products.
        
        Args:
            process: The process whose dependencies to track
            all_processes: All available processes
            visited: Set of already visited resources to avoid cycles
        """
        # Iterate through process needs
        for resource in process.needs:
            # Skip resources that are already visited to avoid cycles
            if resource in visited:
                continue
            
            # Add resource to value chain resources set (even if it's a target)
            self._value_chain_resources.add(resource)
            
            # Add resource to visited set
            visited.add(resource)
            
            # Recursively call for all processes that produce this resource
            for producer in all_processes:
                if resource in producer.results:
                    self._track_dependencies_recursive(producer, all_processes, visited)
    
    def _calculate_downstream_value(self, resource: str) -> float:
        """
        Calculate downstream value of a resource for bottleneck prioritization.
        
        Args:
            resource: The resource name to calculate value for
            
        Returns:
            Downstream value based on importance to high-value processes
        """
        # Calculate value by summing (quantity * 100.0) for all high-value processes that need this resource
        value = 0.0
        for process_name, needs in self._intermediate_needs.items():
            if resource in needs:
                value += needs[resource] * 100.0
        
        # Return calculated value if > 0, otherwise return 10.0 if in value chain, else 0.0
        if value > 0:
            return value
        elif resource in self._value_chain_resources:
            return 10.0
        else:
            return 0.0
    
    def calculate_priority_score(self,
                                 process: Process,
                                 current_stocks: Dict[str, int],
                                 current_cycle: int) -> float:
        """
        Calculate priority score for a single process.
        
        Args:
            process: The process to score
            current_stocks: Current stock levels for all resources
            current_cycle: Current simulation cycle number
            
        Returns:
            Priority score (higher is better)
        """
        # Calculate input cost and output value
        input_cost = 0.0
        output_value = 0.0
        
        for resource, quantity in process.needs.items():
            input_cost += quantity
        
        for resource, quantity in process.results.items():
            output_value += quantity
        
        # Calculate base efficiency score
        if len(process.needs) == 0:
            # Processes with no needs get high base score
            base_score = 100000.0
        elif input_cost > 0:
            efficiency = output_value / input_cost
            base_score = efficiency * 100.0
        else:
            # Handle division by zero
            base_score = output_value * 100.0
        
        score = base_score
        
        # Identify resource gatherers (processes with <= 1 need, consuming target resources)
        is_resource_gatherer = (
            len(process.needs) <= 1 and
            any(target in process.needs for target in self._stock_targets)
        )
        
        # Check if this resource gatherer produces something critically needed
        produces_critical_input = False
        if is_resource_gatherer:
            # Check if we have enough euro reserved for value chain execution
            current_euro = current_stocks.get('euro', 0) if 'euro' in self._stock_targets else float('inf')
            euro_reserve = self._get_effective_reserve('euro', current_cycle)
            has_enough_euro_reserve = current_euro >= euro_reserve
            
            # Only allow resource gathering if we have enough euro reserved OR this produces critical input
            for resource in process.results:
                if resource in self._value_chain_resources:
                    # Check if this resource is critically low
                    current_stock = current_stocks.get(resource, 0)
                    # Check if any process in value chain needs this resource and we don't have enough
                    needed_amount = 0
                    for proc_name in self._intermediate_needs:
                        if resource in self._intermediate_needs[proc_name]:
                            needed_amount += self._intermediate_needs[proc_name][resource] * 20
                    
                    if needed_amount > 0 and current_stock < needed_amount:
                        # Only mark as critical if we have euro reserve OR this doesn't cost euro
                        if has_enough_euro_reserve or 'euro' not in process.needs:
                            produces_critical_input = True
                        break
        
        # Apply target production bonuses with bulk multipliers
        for target in self._stock_targets:
            if target in process.results:
                production = process.results[target]
                consumption = process.needs.get(target, 0)
                net_production = production - consumption
                
                # Check if this process consumes bulk-targeted resources
                consumes_bulk_target = False
                for resource in process.needs:
                    if resource in self._bulk_targets:
                        current_stock = current_stocks.get(resource, 0)
                        bulk_target = self._bulk_targets[resource]
                        if current_stock < bulk_target:
                            # Consuming a resource we need for bulk production
                            consumes_bulk_target = True
                            break
                
                # Check if we're low on euro and this process produces euro
                current_euro = current_stocks.get('euro', 0) if 'euro' in self._stock_targets else 0
                euro_reserve = self._get_effective_reserve('euro', current_cycle)
                low_on_euro = current_euro < euro_reserve
                
                # Heavily penalize processes that consume bulk-targeted resources
                # UNLESS we're low on euro and this produces euro (need to sell to get money)
                if consumes_bulk_target:
                    if low_on_euro and net_production > 0:
                        # Allow selling to get euro when we're low
                        score *= 1.0  # No penalty
                    else:
                        score *= 0.0001  # Massive penalty
                else:
                    # Heavily favor processes with high net production
                    bonus = net_production * 50000.0
                    
                    # Apply bulk multipliers based on net production
                    if net_production > 10000:
                        bonus *= 200.0
                    elif net_production > 1000:
                        bonus *= 80.0
                    elif net_production > 100:
                        bonus *= 30.0
                    elif net_production > 0:
                        bonus *= 10.0
                    
                    score += bonus
        
        # Apply target consumption penalties based on current stock levels
        # But reduce penalty if this process is part of a high-value chain
        for target in self._stock_targets:
            if target in process.needs:
                consumption = process.needs[target]
                current_stock = current_stocks.get(target, 0)
                reserve_needed = self._get_effective_reserve(target, current_cycle)
                available_stock = current_stock - reserve_needed
                
                # If consuming would dip into reserves, apply heavy penalty
                if available_stock < consumption:
                    # Not enough available (after reserves)
                    if process.name in self._high_value_processes:
                        # High-value process can use reserves
                        penalty_factor = 1.0
                    elif process.name in self._intermediate_needs:
                        # Check if this is a resource gatherer (only needs target resources)
                        is_resource_gatherer = (
                            len(process.needs) <= 1 and
                            all(need in self._stock_targets for need in process.needs)
                        )
                        
                        if is_resource_gatherer:
                            # Resource gatherers should NOT use reserves
                            penalty_factor = 10000000.0
                        else:
                            # Value chain processes can use some reserves but with heavy penalty
                            penalty_factor = 100000.0
                    else:
                        # Regular process should not use reserves
                        penalty_factor = 10000000.0
                else:
                    # Calculate penalty factor based on available stock level
                    if available_stock < 100:
                        penalty_factor = 10000.0
                    elif available_stock < 1000:
                        penalty_factor = 1000.0
                    elif available_stock < 10000:
                        penalty_factor = 100.0
                    else:
                        penalty_factor = 10.0
                    
                    # Reduce penalty if process is in value chain
                    if process.name in self._intermediate_needs:
                        penalty_factor *= 0.1
                
                penalty = consumption * penalty_factor
                score -= penalty
        
        # Apply bulk production bonuses/penalties
        for resource in process.results:
            if resource in self._bulk_targets:
                current_stock = current_stocks.get(resource, 0)
                bulk_target = self._bulk_targets[resource]
                
                if current_stock < bulk_target:
                    # Below target - massive boost
                    shortage_ratio = (bulk_target - current_stock) / bulk_target
                    score *= (1000.0 + shortage_ratio * 100000.0)
                else:
                    # Above target - heavy penalty
                    score *= 0.0001
        
        # Apply bulk consumption penalties (with cash-flow mode override)
        consumes_bulk_target = any(resource in self._bulk_targets for resource in process.needs)
        if consumes_bulk_target and not self._cash_flow_mode:
            # Check if we're low on euro
            current_euro = current_stocks.get('euro', 0) if 'euro' in self._stock_targets else float('inf')
            euro_reserve = self._get_effective_reserve('euro', current_cycle)
            low_on_euro = current_euro < euro_reserve
            
            # Check if this process produces euro
            produces_euro = any(
                target in process.results and process.results[target] > process.needs.get(target, 0)
                for target in self._stock_targets
            )
            
            # Check if we have excess of the consumed resource (above bulk target)
            # OR if we have a reasonable amount to sell
            has_excess_or_sellable = False
            for resource in process.needs:
                if resource in self._bulk_targets:
                    current_stock = current_stocks.get(resource, 0)
                    bulk_target = self._bulk_targets[resource]
                    consumption = process.needs[resource]
                    
                    # Allow selling if:
                    # 1. We have excess (above bulk target)
                    # 2. We have at least 2x what we need (can afford to sell some)
                    # 3. This process produces target resources (selling for money)
                    # 4. We have at least 10% of bulk target (progressive accumulation)
                    if (current_stock > bulk_target or 
                        current_stock >= consumption * 2 or
                        produces_euro or
                        current_stock >= bulk_target * 0.1):
                        has_excess_or_sellable = True
                        break
            
            # Apply penalty unless:
            # 1. We're low on euro and this produces euro (need money)
            # 2. We have excess or sellable amount of the consumed resource
            if not ((low_on_euro and produces_euro) or has_excess_or_sellable):
                score *= 0.0001
        
        # Apply phase-based multipliers (with cash-flow mode override)
        if self._analyzed:
            # In cash-flow mode, allow resource gatherers to restart production
            if self._cash_flow_mode and is_resource_gatherer:
                score *= 100.0  # Strong boost to break deadlock
            
            # Task 6.1: Gathering phase multipliers
            elif self._current_phase == "gathering":
                if is_resource_gatherer:
                    score *= 2.0
            
            # Task 6.2: Production phase multipliers
            elif self._current_phase == "production":
                if is_resource_gatherer:
                    if not produces_critical_input:
                        score *= 0.0001
                
                # Boost processes producing deep value chain resources (depth >= 2)
                for resource in process.results:
                    depth = self._value_chain_depth.get(resource, 0)
                    if depth >= 2:
                        score *= 50.0
                        break
            
            # Task 6.3: Conversion phase multipliers
            elif self._current_phase == "conversion":
                if is_resource_gatherer:
                    if not produces_critical_input:
                        score *= 0.000001
                
                # Boost processes producing direct high-value inputs (depth == 1)
                for resource in process.results:
                    depth = self._value_chain_depth.get(resource, 0)
                    if depth == 1:
                        score *= 500.0
                        break
                    elif depth == 2:
                        score *= 100.0
                        break
            
            # Task 6.4: Selling phase multipliers
            elif self._current_phase == "selling":
                if is_resource_gatherer:
                    if not produces_critical_input:
                        score *= 0.00000001
                
                # Penalize non-high-value processes
                if process.name not in self._high_value_processes:
                    score *= 0.01
        
        # Apply value chain scarcity multipliers
        for resource in process.results:
            if resource in self._value_chain_resources:
                current_stock = current_stocks.get(resource, 0)
                
                # Apply scarcity multiplier
                if current_stock == 0:
                    score *= 5.0
                elif current_stock < 10:
                    score *= 3.0
                elif current_stock < 30:
                    score *= 2.0
        
        # Penalize processes that produce and consume the same resource (loops)
        # UNLESS they produce something needed for bulk targets
        produces_bulk_needed = any(r in self._bulk_targets for r in process.results)
        for resource in process.results:
            if resource in process.needs:
                # This is likely a conversion loop
                if produces_bulk_needed:
                    score *= 0.5  # Moderate penalty if producing bulk-needed resource
                else:
                    score *= 0.01  # Heavy penalty otherwise
        
        # Penalize processes that create indirect conversion loops
        # (e.g., separation_oeuf -> reunion_oeuf)
        # Check if this process's outputs are consumed by another process that produces this process's inputs
        creates_conversion_loop = False
        for result_resource in process.results:
            for need_resource in process.needs:
                # Check if there's a process that consumes result_resource and produces need_resource
                for other_process in self._all_processes:
                    if (result_resource in other_process.needs and 
                        need_resource in other_process.results and
                        other_process.name != process.name):
                        # This creates a conversion loop
                        creates_conversion_loop = True
                        break
                if creates_conversion_loop:
                    break
            if creates_conversion_loop:
                break
        
        if creates_conversion_loop:
            # Apply massive penalty to conversion loops unless they produce bulk-needed resources
            if not produces_bulk_needed:
                score *= 0.00001  # Essentially block these processes
        
        # Boost selling processes when we need euros (before penalties)
        # Check if this process produces target resources without consuming them
        is_selling_process = False
        for target in self._stock_targets:
            if target in process.results and target not in process.needs:
                is_selling_process = True
                break
        
        if is_selling_process:
            current_euro = current_stocks.get('euro', 0) if 'euro' in self._stock_targets else float('inf')
            euro_reserve = self._get_effective_reserve('euro', current_cycle)
            
            # If we're below reserve, heavily boost selling processes
            if current_euro < euro_reserve:
                score += 1000000.0  # Add large bonus instead of multiplying
            # Even if above reserve, give a moderate boost to keep money flowing
            else:
                score += 10000.0
        
        # Apply delay penalty
        score -= process.delay * 1.0
        
        # Apply execution count penalty (encourages diversity)
        score -= process.execution_count * 0.1
        
        return score
    
    def _get_effective_reserve(self, target: str, current_cycle: int) -> int:
        """
        Calculate effective reserve based on current phase and progress.
        
        In early phases, use lower reserves to allow initial resource gathering.
        In later phases, use full reserves to protect resources for bulk execution.
        
        Args:
            target: The target resource (e.g., 'euro')
            current_cycle: Current simulation cycle
            
        Returns:
            Effective reserve amount
        """
        base_reserve = self._target_reserve_needed.get(target, 0)
        
        if base_reserve == 0:
            return 0
        
        # In gathering phase, use only 0.1% of reserve to allow initial buying
        # This ensures we can start buying even with large reserves
        if self._current_phase == "gathering":
            return int(base_reserve * 0.001)
        # In production phase, use 10% of reserve
        elif self._current_phase == "production":
            return int(base_reserve * 0.1)
        # In conversion phase, use 50% of reserve
        elif self._current_phase == "conversion":
            return int(base_reserve * 0.5)
        # In selling phase, use full reserve
        else:
            return base_reserve
    
    def _detect_phase(self, current_stocks: Dict[str, int], current_cycle: int) -> str:
        """
        Detect which phase of optimization we're in.
        
        Returns:
            Phase name: "gathering", "production", "conversion", or "selling"
        """
        if not self._analyzed or not self._stock_targets:
            return "gathering"
        
        # Force selling phase at 80% of total cycles for long simulations
        if self._total_cycles > 0 and current_cycle >= int(self._total_cycles * 0.8):
            return "selling"
        
        # Force transition out of gathering after limit
        if current_cycle > self._gathering_limit_cycle and self._current_phase == "gathering":
            return "production"
        
        # Check if we have enough intermediate resources to start production
        total_value_chain_stock = 0
        total_value_chain_needed = 0
        
        for resource in self._value_chain_resources:
            if resource not in self._stock_targets:
                current_stock = current_stocks.get(resource, 0)
                total_value_chain_stock += current_stock
                
                # Calculate how much we need
                for hv_process_name in self._high_value_processes:
                    if hv_process_name in self._intermediate_needs:
                        total_value_chain_needed += self._intermediate_needs[hv_process_name].get(resource, 0) * 10
        
        # Check if we can execute high-value processes
        can_execute_hv = False
        for hv_process_name in self._high_value_processes:
            for process in self._all_processes:
                if process.name == hv_process_name:
                    can_execute = all(
                        current_stocks.get(resource, 0) >= quantity
                        for resource, quantity in process.needs.items()
                    )
                    if can_execute:
                        can_execute_hv = True
                        break
            if can_execute_hv:
                break
        
        # Phase detection logic with cycle-based transitions
        # Adjust thresholds proportionally for long simulations
        production_threshold = 500
        conversion_threshold = 1000
        
        if self._is_long_simulation:
            # Scale thresholds proportionally (e.g., for 50K cycles, scale by factor of ~50)
            scale_factor = self._total_cycles / 1000.0
            production_threshold = int(500 * scale_factor / 50.0)  # Keep reasonable thresholds
            conversion_threshold = int(1000 * scale_factor / 50.0)
        
        if can_execute_hv:
            return "selling"
        elif current_cycle > conversion_threshold or (total_value_chain_needed > 0 and total_value_chain_stock > total_value_chain_needed * 0.2):
            return "conversion"
        elif current_cycle > production_threshold or (total_value_chain_needed > 0 and total_value_chain_stock > total_value_chain_needed * 0.02):
            return "production"
        else:
            return "gathering"
    
    def select_best_process(self,
                           available_processes: List[Process],
                           current_stocks: Dict[str, int],
                           current_cycle: int) -> Optional[Process]:
        """
        Select the best process to execute from available candidates.
        
        Args:
            available_processes: List of processes that can currently execute
            current_stocks: Current stock levels for all resources
            current_cycle: Current simulation cycle number
            
        Returns:
            Best process to execute, or None if no good options
        """
        # Task 4.1: Initial checks
        # Return None if available_processes is empty
        if not available_processes:
            return None
        
        # If not analyzed, accumulate processes to _all_processes list
        if not self._analyzed:
            for process in available_processes:
                # Avoid duplicates
                if process not in self._all_processes:
                    self._all_processes.append(process)
            
            # Trigger analysis when _all_processes has > 10 processes
            if len(self._all_processes) > 10:
                self._analyze_value_chains(self._all_processes)
        
        # Detect current phase
        if self._analyzed:
            new_phase = self._detect_phase(current_stocks, current_cycle)
            if new_phase != self._current_phase:
                self._current_phase = new_phase
                self._phase_transition_cycle = current_cycle
        
        # Task 4.2 & 7.1: Enhanced bottleneck detection with bulk awareness
        # Check for critical bottlenecks (resources in value chain with stock below bulk targets)
        bottleneck_producers = []
        blocking_resources = {}  # Track resources blocking high-value processes
        
        # First, check if we're missing resources needed directly by high-value processes
        # AND by intermediate processes in the value chain
        for proc_name in self._intermediate_needs:
            for resource, quantity in self._intermediate_needs[proc_name].items():
                current_stock = current_stocks.get(resource, 0)
                # Determine multiplier based on whether this is a high-value process
                if proc_name in self._high_value_processes:
                    multiplier = 100
                    base_value = 1000000.0
                else:
                    multiplier = 50
                    base_value = 500000.0
                
                # If we don't have enough of a resource needed by value chain process
                if current_stock < quantity * multiplier:
                    # Find processes that produce this resource
                    for process in available_processes:
                        if resource in process.results:
                            # Very high priority - this enables value chain execution
                            downstream_value = base_value
                            urgency = (quantity * multiplier - current_stock) * 1000.0
                            bottleneck_producers.append((process, downstream_value + urgency, resource))
        
        # Task 7.1: Check value chain resources against bulk targets (not just stock < 10)
        for resource in self._value_chain_resources:
            current_stock = current_stocks.get(resource, 0)
            
            # Check if this resource has a bulk target
            bulk_threshold = self._bulk_targets.get(resource, 0)
            
            # Task 7.1: Prioritize bulk targets over absolute thresholds
            if bulk_threshold > 0:
                # Resource has a bulk target - check against it
                if current_stock < bulk_threshold:
                    # Find processes that produce this bottleneck resource
                    for process in available_processes:
                        if resource in process.results:
                            # Calculate downstream value for this producer
                            downstream_value = self._calculate_downstream_value(resource)
                            # Task 7.1: Calculate urgency as shortage * 1000.0
                            shortage = bulk_threshold - current_stock
                            urgency = shortage * 1000.0
                            bottleneck_producers.append((process, downstream_value + urgency, resource))
            else:
                # No bulk target - use absolute threshold (stock < 10)
                if current_stock < 10:
                    # Find processes that produce this bottleneck resource
                    for process in available_processes:
                        if resource in process.results:
                            # Calculate downstream value for this producer
                            downstream_value = self._calculate_downstream_value(resource)
                            urgency = (10 - current_stock) * 1000.0
                            bottleneck_producers.append((process, downstream_value + urgency, resource))
        
        # Task 6.2: Check if high-value processes can execute and track blocking resources
        # Check both single execution and bulk execution (quantity * 100)
        for hv_process_name in self._high_value_processes:
            # Find the high-value process
            hv_process = None
            for p in self._all_processes:
                if p.name == hv_process_name:
                    hv_process = p
                    break
            
            if hv_process:
                # Check if we can execute this high-value process (single and bulk)
                for resource, quantity in hv_process.needs.items():
                    current_stock = current_stocks.get(resource, 0)
                    bulk_quantity = quantity * 100
                    
                    if current_stock < quantity:
                        # This resource is blocking single HV execution
                        if resource not in blocking_resources:
                            blocking_resources[resource] = (quantity, current_stock)
                        else:
                            # Update if this HV process needs more
                            existing_needed, existing_have = blocking_resources[resource]
                            blocking_resources[resource] = (max(existing_needed, quantity), current_stock)
                    elif current_stock < bulk_quantity:
                        # Can execute once but not in bulk - track bulk requirement
                        if resource not in blocking_resources:
                            blocking_resources[resource] = (bulk_quantity, current_stock)
                        else:
                            # Update if this HV process needs more for bulk
                            existing_needed, existing_have = blocking_resources[resource]
                            blocking_resources[resource] = (max(existing_needed, bulk_quantity), current_stock)
        
        # Task 6.3: If in conversion/selling phase and blocked, force production of blocking resources
        if self._current_phase in ["conversion", "selling"] and blocking_resources:
            for resource, (needed, have) in blocking_resources.items():
                for process in available_processes:
                    if resource in process.results:
                        # Force this process with maximum priority
                        shortage = needed - have
                        urgency = shortage * 10000.0  # Very high urgency for blocking resources
                        bottleneck_producers.append((process, 10000000.0 + urgency, resource))
        
        # Return producer with highest downstream value if bottlenecks exist
        # Prioritize by urgency (highest shortage first)
        # But filter out processes that would consume reserved target resources or create loops
        if bottleneck_producers:
            # Filter bottleneck producers to exclude those that can't afford to run or create loops
            affordable_bottleneck_producers = []
            for process, priority, resource in bottleneck_producers:
                # Check if this process creates a conversion loop
                creates_conversion_loop = False
                for result_resource in process.results:
                    for need_resource in process.needs:
                        for other_process in self._all_processes:
                            if (result_resource in other_process.needs and 
                                need_resource in other_process.results and
                                other_process.name != process.name):
                                creates_conversion_loop = True
                                break
                        if creates_conversion_loop:
                            break
                    if creates_conversion_loop:
                        break
                
                # Skip conversion loops unless they produce bulk-needed resources
                if creates_conversion_loop:
                    produces_bulk_needed = any(r in self._bulk_targets for r in process.results)
                    if not produces_bulk_needed:
                        continue  # Skip this process
                
                # Check if this process consumes target resources below reserve
                # Allow in gathering phase or cash-flow mode
                can_afford = True
                if not (self._current_phase == "gathering" or self._cash_flow_mode):
                    for target in self._stock_targets:
                        if target in process.needs:
                            consumption = process.needs[target]
                            current_stock = current_stocks.get(target, 0)
                            reserve_needed = self._get_effective_reserve(target, current_cycle)
                            available_stock = current_stock - reserve_needed
                            
                            # If this would consume reserved resources, check if it's allowed
                            if available_stock < consumption:
                                # Only high-value processes and value chain processes can use reserves
                                if process.name not in self._high_value_processes:
                                    # Check if it's a resource gatherer
                                    is_resource_gatherer = (
                                        len(process.needs) <= 1 and
                                        all(need in self._stock_targets for need in process.needs)
                                    )
                                    if is_resource_gatherer:
                                        # Resource gatherers cannot use reserves
                                        can_afford = False
                                        break
                
                if can_afford:
                    affordable_bottleneck_producers.append((process, priority, resource))
            
            if affordable_bottleneck_producers:
                affordable_bottleneck_producers.sort(key=lambda x: x[1], reverse=True)
                # Return the most urgent affordable bottleneck producer
                best_bottleneck = affordable_bottleneck_producers[0][0]
                return best_bottleneck
        
        # Task 4.3: Scoring and selection
        # Check if we have sufficient resources to start executing high-value processes
        # and identify what's blocking the ENTIRE value chain
        can_execute_hv = False
        
        for hv_process_name in self._high_value_processes:
            # Find the process
            hv_process = None
            for p in self._all_processes:
                if p.name == hv_process_name:
                    hv_process = p
                    break
            
            if hv_process:
                # Check if we can execute this high-value process
                can_execute = True
                for resource, quantity in hv_process.needs.items():
                    current_stock = current_stocks.get(resource, 0)
                    # Check for bulk execution (100x)
                    bulk_quantity = quantity * 100
                    if current_stock < quantity:
                        can_execute = False
                        if resource not in blocking_resources:
                            blocking_resources[resource] = (quantity, current_stock)
                    elif current_stock < bulk_quantity:
                        # Can execute once but not in bulk - track as partial block
                        if resource not in blocking_resources:
                            blocking_resources[resource] = (bulk_quantity, current_stock)
                
                if can_execute:
                    can_execute_hv = True
                    # Don't break - keep checking for bulk requirements
        
        # Also check intermediate value chain processes for blocking
        for proc_name in self._intermediate_needs:
            for proc in self._all_processes:
                if proc.name == proc_name:
                    for resource, quantity in proc.needs.items():
                        if resource not in self._stock_targets:
                            current_stock = current_stocks.get(resource, 0)
                            # Check if we need bulk amounts
                            bulk_quantity = quantity * 100
                            if current_stock < bulk_quantity:
                                if resource not in blocking_resources:
                                    blocking_resources[resource] = (bulk_quantity, current_stock)
                    break
        
        # Score all available processes using calculate_priority_score
        scored_processes = []
        for process in available_processes:
            score = self.calculate_priority_score(process, current_stocks, current_cycle)
            
            # Initialize flags
            produces_critical_resource = False
            process_depth = 0
            
            # Task 7.1: Enhanced high-value process boost logic
            if process.name in self._high_value_processes:
                # Check if HV process can execute (has all intermediate resources)
                can_execute_once = True
                can_execute_bulk = True
                
                for resource, quantity in process.needs.items():
                    current_stock = current_stocks.get(resource, 0)
                    
                    # Check if can execute once
                    if current_stock < quantity:
                        can_execute_once = False
                        can_execute_bulk = False
                        break
                    
                    # Check if can execute in bulk (100x)
                    bulk_quantity = quantity * 100
                    if current_stock < bulk_quantity:
                        can_execute_bulk = False
                
                # Apply boosts based on execution capability
                if can_execute_bulk:
                    # Can execute in bulk (has resources for 100x)
                    if self._current_phase in ["conversion", "selling"]:
                        score *= 10000000.0  # 10,000,000x boost in conversion/selling phases
                    else:
                        score *= 1000000.0  # 1,000,000x boost in other phases
                elif can_execute_once:
                    # Can execute once but not in bulk
                    score *= 100.0  # 100x boost
                else:
                    # Cannot execute - deprioritize
                    if self._current_phase == "gathering":
                        score *= 0.01  # Low priority in gathering phase
                    else:
                        score *= 0.001  # Very low priority if we should have resources by now
            
            # Task 7.2: Value chain resource boost logic
            for resource in process.results:
                # Check if process produces resources needed by high-value processes
                for hv_process_name in self._high_value_processes:
                    for hv_process in self._all_processes:
                        if hv_process.name == hv_process_name and resource in hv_process.needs:
                            # This process produces something needed by HV process
                            hv_quantity_needed = hv_process.needs[resource]
                            current_stock = current_stocks.get(resource, 0)
                            
                            # Calculate total_needed = quantity * 100 for bulk requirements
                            total_needed = hv_quantity_needed * 100
                            
                            # Apply boost if below target
                            if current_stock < total_needed:
                                shortage = total_needed - current_stock
                                # Apply boost_factor = 100.0 + min(shortage / 10.0, 1,000.0)
                                boost_factor = 100.0 + min(shortage / 10.0, 1000.0)
                                score *= boost_factor
                                # Mark process as producing critical resource for sorting
                                produces_critical_resource = True
                                process_depth = 1
            
            # Phase-based prioritization
            is_resource_gatherer = (
                len(process.needs) <= 1 and
                any(target in process.needs for target in self._stock_targets)
            )
            
            # Check if this resource gatherer produces something critically needed
            produces_critical_input = False
            if is_resource_gatherer:
                # Check if we have enough euro reserved for value chain execution
                current_euro = current_stocks.get('euro', 0) if 'euro' in self._stock_targets else float('inf')
                euro_reserve = self._get_effective_reserve('euro', current_cycle)
                has_enough_euro_reserve = current_euro >= euro_reserve
                
                # Only allow resource gathering if we have enough euro reserved OR this produces critical input
                for resource in process.results:
                    if resource in self._value_chain_resources:
                        # Check if this resource is critically low
                        current_stock = current_stocks.get(resource, 0)
                        # Check if any process in value chain needs this resource and we don't have enough
                        needed_amount = 0
                        for proc_name in self._intermediate_needs:
                            if resource in self._intermediate_needs[proc_name]:
                                needed_amount += self._intermediate_needs[proc_name][resource] * 20
                        
                        if needed_amount > 0 and current_stock < needed_amount:
                            # Only mark as critical if we have euro reserve OR this doesn't cost euro
                            if has_enough_euro_reserve or 'euro' not in process.needs:
                                produces_critical_input = True
                            break
            
            if self._current_phase == "gathering":
                # In gathering phase, prioritize resource acquisition
                if is_resource_gatherer:
                    score *= 2.0
            elif self._current_phase == "production":
                # In production phase, penalize resource gathering unless critical
                if is_resource_gatherer and process.name not in self._high_value_processes:
                    if produces_critical_input:
                        score *= 5.0  # Boost if producing critical input
                    else:
                        score *= 0.0001
                
                # Prioritize building intermediate products
                for resource in process.results:
                    if resource in self._value_chain_resources:
                        depth = self._value_chain_depth.get(resource, 0)
                        if depth >= 2:  # Deep in value chain
                            score *= 50.0
                            process_depth = depth
                            produces_critical_resource = True
            elif self._current_phase == "conversion":
                # In conversion phase, penalize resource gathering unless critical
                if is_resource_gatherer and process.name not in self._high_value_processes:
                    if produces_critical_input:
                        score *= 10.0  # Higher boost in conversion phase
                    else:
                        score *= 0.000001
                
                # Prioritize processes closer to high-value
                for resource in process.results:
                    if resource in self._value_chain_resources:
                        depth = self._value_chain_depth.get(resource, 0)
                        if depth == 1:  # Direct input to high-value process
                            score *= 500.0
                            process_depth = depth
                            produces_critical_resource = True
                        elif depth == 2:
                            score *= 100.0
                            process_depth = depth
                            produces_critical_resource = True
            elif self._current_phase == "selling":
                # In selling phase, allow critical resource gathering
                if is_resource_gatherer and process.name not in self._high_value_processes:
                    if produces_critical_input:
                        score *= 50.0  # Very high boost for critical inputs
                    else:
                        score *= 0.00000001
                
                if process.name not in self._high_value_processes:
                    score *= 0.01  # Deprioritize everything else
            
            # If we can execute high-value processes, deprioritize resource gathering
            if can_execute_hv:
                is_resource_gatherer = (
                    len(process.needs) <= 1 and
                    any(target in process.needs for target in self._stock_targets)
                )
                if is_resource_gatherer and process.name not in self._high_value_processes:
                    score *= 0.00001  # Very heavy penalty
            
            # Apply value chain resource boost for intermediate producers
            for resource in process.results:
                if resource in self._value_chain_resources:
                    # Check if any high-value process needs this resource
                    needed_by_hv = False
                    for hv_process_name in self._high_value_processes:
                        if hv_process_name in self._intermediate_needs:
                            if resource in self._intermediate_needs[hv_process_name]:
                                needed_by_hv = True
                                break
                    
                    if needed_by_hv:
                        # This produces something directly needed by high-value process
                        current_stock = current_stocks.get(resource, 0)
                        
                        # Calculate how much we need (multiply by large factor for bulk processes)
                        total_needed = 0
                        for hv_process_name in self._high_value_processes:
                            if hv_process_name in self._intermediate_needs:
                                quantity_needed = self._intermediate_needs[hv_process_name].get(resource, 0)
                                # Multiply by 100 to account for bulk requirements
                                total_needed += quantity_needed * 100
                        
                        # Boost if we don't have enough
                        if current_stock < total_needed:
                            shortage = total_needed - current_stock
                            boost_factor = 100.0 + min(shortage / 10.0, 1000.0)
                            score *= boost_factor
                            produces_critical_resource = True
                            if process_depth == 0:
                                process_depth = 1
                    else:
                        # General value chain resource
                        current_stock = current_stocks.get(resource, 0)
                        if current_stock < 100:
                            score *= 5.0
                        elif current_stock < 1000:
                            score *= 2.0
                    
                    break  # Only apply once per process
            
            # Additional boost for processes that produce resources needed by value chain
            # but are currently at zero or very low stock
            for resource in process.results:
                if resource in self._value_chain_resources:
                    current_stock = current_stocks.get(resource, 0)
                    bulk_target = self._bulk_targets.get(resource, 0)
                    
                    if bulk_target > 0:
                        if current_stock < bulk_target:
                            # This resource has a bulk target and we're below it
                            shortage_ratio = (bulk_target - current_stock) / bulk_target
                            score *= (1000.0 + shortage_ratio * 100000.0)
                            produces_critical_resource = True
                        else:
                            # We're above the bulk target - heavily deprioritize
                            score *= 0.0001
                    elif current_stock == 0:
                        # Critical shortage - massive boost
                        score *= 100000.0
                        produces_critical_resource = True
                    elif current_stock < 5:
                        # Very low stock - large boost
                        score *= 10000.0
                        produces_critical_resource = True
            
            scored_processes.append((process, score, produces_critical_resource, process_depth))
        
        # Filter out processes with negative scores
        positive_scored_processes = [(p, s, c, d) for p, s, c, d in scored_processes if s > 0]
        
        # Cash-flow mode: Detect stalls and temporarily allow buying
        if not positive_scored_processes:
            self._stuck_counter += 1
            
            # If stuck for 3+ cycles, enter cash-flow mode
            if self._stuck_counter >= 3:
                self._cash_flow_mode = True
                
                # Re-score all processes with cash-flow mode enabled
                scored_processes = []
                for process in available_processes:
                    score = self.calculate_priority_score(process, current_stocks, current_cycle)
                    scored_processes.append((process, score, False, 0))
                
                positive_scored_processes = [(p, s, c, d) for p, s, c, d in scored_processes if s > 0]
                
                # If still no positive scores, return None (truly stuck)
                if not positive_scored_processes:
                    return None
        else:
            # Reset stuck counter and exit cash-flow mode if we have positive scores
            self._stuck_counter = 0
            if self._cash_flow_mode:
                self._cash_flow_mode = False
        
        # Final safety check
        if not positive_scored_processes:
            return None
        
        # Sort processes: first by critical resources, then by depth (lower is closer to HV), then by score
        positive_scored_processes.sort(key=lambda x: (x[2], -x[3] if x[3] > 0 else 0, x[1]), reverse=True)
        
        # Update last selection cycle
        self._last_selection_cycle = current_cycle
        
        # Return process with highest priority
        return positive_scored_processes[0][0]
