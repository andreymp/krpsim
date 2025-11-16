from typing import Dict, List, Optional, Set
from src.common import Process


class UniversalOptimizer:
    """Universal optimizer that works for any configuration."""
    
    def __init__(self, optimization_targets: List[str], all_processes: Optional[List[Process]] = None):
        """
        Initialize optimizer with targets and optionally all processes.
        
        Args:
            optimization_targets: List of resources to optimize (or "time")
            all_processes: Optional list of all processes for upfront analysis
        """
        # Configuration
        self._optimization_targets = optimization_targets.copy()
        self._stock_targets = [t for t in optimization_targets if t != 'time']
        self._time_optimization_enabled = 'time' in optimization_targets
        
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
        
        # Perform upfront analysis if all processes provided
        if self._all_processes:
            self._analyze_value_chains(self._all_processes)
    
    def _analyze_value_chains(self, all_processes: List[Process]) -> None:
        """
        Identify high-value processes and their complete dependency chains.
        
        High-value processes are those that produce significant amounts of target resources.
        This method also tracks all intermediate resources needed in the value chain.
        """
        # Early return if already analyzed or no stock targets
        if self._analyzed or not self._stock_targets:
            return
        
        # Iterate through all processes to identify high-value processes
        for process in all_processes:
            for target in self._stock_targets:
                if target in process.results:
                    production = process.results[target]
                    consumption = process.needs.get(target, 0)
                    net_production = production - consumption
                    
                    # Check high-value criteria
                    is_high_value = (
                        net_production > 1000 or
                        (consumption > 0 and net_production > 50 * consumption) or
                        production > 10000
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
        
        # Reserve target resources for ALL value chain processes (not just high-value)
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
                        # Calculate minimum reserve needed (multiply by expected executions)
                        if process.name in self._high_value_processes:
                            multiplier = 100  # Reserve for 100 executions of HV process
                        else:
                            multiplier = 500  # Reserve much more for intermediate processes
                        
                        needed = process.needs[target] * multiplier
                        if target not in self._target_reserve_needed:
                            self._target_reserve_needed[target] = needed
                        else:
                            # Use max instead of sum to avoid over-reserving
                            self._target_reserve_needed[target] = max(self._target_reserve_needed[target], needed)
        
        # Calculate bulk production targets for direct HV process inputs
        for hv_process_name in self._high_value_processes:
            for process in all_processes:
                if process.name == hv_process_name:
                    for resource, quantity in process.needs.items():
                        if resource not in self._stock_targets:
                            # This resource is needed in bulk (100x) for HV process
                            bulk_amount = quantity * 100
                            self._bulk_targets[resource] = bulk_amount
                    break
        
        # Also calculate bulk targets for inputs to processes that produce bulk-targeted resources
        # (one level of recursion)
        bulk_resources = list(self._bulk_targets.keys())
        for resource in bulk_resources:
            bulk_amount = self._bulk_targets[resource]
            # Find processes that produce this resource
            for producer in all_processes:
                if resource in producer.results:
                    production_per_run = producer.results[resource]
                    runs_needed = (bulk_amount + production_per_run - 1) // production_per_run
                    # Calculate what this producer needs
                    for producer_need, producer_need_qty in producer.needs.items():
                        if producer_need not in self._stock_targets:
                            total_needed = producer_need_qty * runs_needed
                            if producer_need not in self._bulk_targets:
                                self._bulk_targets[producer_need] = total_needed
                            else:
                                self._bulk_targets[producer_need] = max(self._bulk_targets[producer_need], total_needed)
        
        # Mark analysis as complete
        self._analyzed = True
    
    def _calculate_bulk_targets_recursive(self, all_processes: List[Process], depth: int = 0, max_depth: int = 3) -> None:
        """Recursively calculate bulk production targets for the entire value chain."""
        if depth >= max_depth:
            return
        
        # Start with high-value processes
        if depth == 0:
            for hv_process_name in self._high_value_processes:
                for process in all_processes:
                    if process.name == hv_process_name:
                        for resource, quantity in process.needs.items():
                            if resource not in self._stock_targets:
                                # This resource is needed in bulk (100x) for HV process
                                bulk_amount = quantity * 100
                                if resource not in self._bulk_targets:
                                    self._bulk_targets[resource] = bulk_amount
                                else:
                                    self._bulk_targets[resource] = max(self._bulk_targets[resource], bulk_amount)
                        break
        
        # For each resource with a bulk target, find producers and calculate their needs
        # But reduce the multiplier as we go deeper to avoid over-production
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
                            # Reduce target as we go deeper (50% per level)
                            reduction_factor = 0.5 ** depth
                            total_needed = int(producer_need_qty * runs_needed * reduction_factor)
                            if total_needed > 0:
                                if producer_need not in self._bulk_targets:
                                    self._bulk_targets[producer_need] = total_needed
                                else:
                                    self._bulk_targets[producer_need] = max(self._bulk_targets[producer_need], total_needed)
        
        # Recurse to handle dependencies of dependencies
        if depth < max_depth - 1:
            self._calculate_bulk_targets_recursive(all_processes, depth + 1, max_depth)
    
    def _calculate_value_chain_depth(self, all_processes: List[Process]) -> None:
        """Calculate the depth of each resource in the value chain."""
        # Start with high-value processes at depth 0
        for hv_process_name in self._high_value_processes:
            for process in all_processes:
                if process.name == hv_process_name:
                    for resource in process.needs:
                        if resource not in self._value_chain_depth:
                            self._value_chain_depth[resource] = 1
        
        # Recursively calculate depth for dependencies
        changed = True
        max_iterations = 10
        iteration = 0
        while changed and iteration < max_iterations:
            changed = False
            iteration += 1
            for process in all_processes:
                for result_resource in process.results:
                    if result_resource in self._value_chain_depth:
                        result_depth = self._value_chain_depth[result_resource]
                        for need_resource in process.needs:
                            if need_resource not in self._stock_targets:
                                new_depth = result_depth + 1
                                if need_resource not in self._value_chain_depth or self._value_chain_depth[need_resource] < new_depth:
                                    self._value_chain_depth[need_resource] = new_depth
                                    changed = True
    
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
                euro_reserve = self._target_reserve_needed.get('euro', 0)
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
                reserve_needed = self._target_reserve_needed.get(target, 0)
                available_stock = current_stock - reserve_needed
                
                # If consuming would dip into reserves, apply heavy penalty
                if available_stock < consumption:
                    # Not enough available (after reserves)
                    if process.name in self._high_value_processes:
                        # High-value process can use reserves
                        penalty_factor = 1.0
                    elif process.name in self._intermediate_needs:
                        # Value chain process can use some reserves but with penalty
                        penalty_factor = 1000.0
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
        for resource in process.results:
            if resource in process.needs:
                # This is likely a conversion loop - heavily penalize
                score *= 0.01
        
        # Apply delay penalty
        score -= process.delay * 1.0
        
        # Apply execution count penalty (encourages diversity)
        score -= process.execution_count * 0.1
        
        return score
    
    def _detect_phase(self, current_stocks: Dict[str, int], current_cycle: int) -> str:
        """
        Detect which phase of optimization we're in.
        
        Returns:
            Phase name: "gathering", "production", "conversion", or "selling"
        """
        if not self._analyzed or not self._stock_targets:
            return "gathering"
        
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
        # Adjusted for long simulations (50K cycles)
        if can_execute_hv:
            return "selling"
        elif current_cycle > 1000 or (total_value_chain_needed > 0 and total_value_chain_stock > total_value_chain_needed * 0.2):
            return "conversion"
        elif current_cycle > 500 or (total_value_chain_needed > 0 and total_value_chain_stock > total_value_chain_needed * 0.02):
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
        
        # Task 4.2: Bottleneck detection and backward planning
        # Check for critical bottlenecks (resources in value chain with stock = 0 or very low)
        bottleneck_producers = []
        blocking_resources = {}  # Initialize here for broader scope
        
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
        
        # Then check general value chain resources and bulk targets
        for resource in self._value_chain_resources:
            current_stock = current_stocks.get(resource, 0)
            
            # Check if this resource has a bulk target
            bulk_threshold = self._bulk_targets.get(resource, 0)
            
            # Check if this resource is critically low (either absolute or relative to bulk needs)
            is_critical = current_stock < 10 or (bulk_threshold > 0 and current_stock < bulk_threshold)
            
            if is_critical:
                # Find processes that produce this bottleneck resource
                for process in available_processes:
                    if resource in process.results:
                        # Calculate downstream value for this producer
                        downstream_value = self._calculate_downstream_value(resource)
                        # Add urgency factor based on bulk target
                        if bulk_threshold > 0:
                            shortage = bulk_threshold - current_stock
                            urgency = shortage * 1000.0  # High urgency for bulk targets
                        else:
                            urgency = (10 - current_stock) * 1000.0
                        bottleneck_producers.append((process, downstream_value + urgency, resource))
        
        # If we're in conversion/selling phase and blocked, force production of blocking resources
        if self._current_phase in ["conversion", "selling"] and blocking_resources:
            for resource, (needed, have) in blocking_resources.items():
                for process in available_processes:
                    if resource in process.results:
                        # Force this process with maximum priority
                        bottleneck_producers.append((process, 10000000.0, resource))
        
        # Return producer with highest downstream value if bottlenecks exist
        if bottleneck_producers:
            bottleneck_producers.sort(key=lambda x: x[1], reverse=True)
            return bottleneck_producers[0][0]
        
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
            
            # Apply high-value process boost
            if process.name in self._high_value_processes:
                # Check if we have enough intermediate resources to execute
                missing_resources = []
                bulk_needed = 0
                for resource, quantity in process.needs.items():
                    if resource not in self._stock_targets:
                        current_stock = current_stocks.get(resource, 0)
                        # For bulk processes, check if we have enough for many executions
                        bulk_quantity = quantity * 100
                        if current_stock < bulk_quantity:
                            bulk_needed += (bulk_quantity - current_stock)
                        if current_stock < quantity:
                            missing_resources.append((resource, quantity - current_stock))
                
                if not missing_resources:
                    # Can execute high-value process - massive boost
                    if self._current_phase in ["conversion", "selling"]:
                        score *= 10000000.0  # Even higher boost in later phases
                    else:
                        score *= 1000000.0
                elif bulk_needed > 0:
                    # Have enough for single execution but not bulk - moderate priority
                    score *= 100.0
                else:
                    # Missing intermediate resources - work backwards to build them
                    if self._current_phase == "gathering":
                        score *= 0.01  # Low priority in gathering phase
                    else:
                        score *= 0.001  # Very low priority if we should have resources by now
            
            # Boost processes that produce resources needed in bulk by high-value processes
            for resource in process.results:
                for hv_process_name in self._high_value_processes:
                    for hv_process in self._all_processes:
                        if hv_process.name == hv_process_name and resource in hv_process.needs:
                            # This process produces something needed by HV process
                            hv_quantity_needed = hv_process.needs[resource]
                            current_stock = current_stocks.get(resource, 0)
                            # Check if we need bulk amounts (100x for vente_boite)
                            bulk_target = hv_quantity_needed * 100
                            if current_stock < bulk_target:
                                # Massive boost to build up bulk resources
                                shortage_factor = (bulk_target - current_stock) / bulk_target
                                score *= (1000.0 * shortage_factor)
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
                euro_reserve = self._target_reserve_needed.get('euro', 0)
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
                    if current_stock == 0:
                        # Critical shortage - massive boost
                        score *= 100000.0
                        produces_critical_resource = True
                    elif current_stock < 5:
                        # Very low stock - large boost
                        score *= 10000.0
                        produces_critical_resource = True
            
            scored_processes.append((process, score, produces_critical_resource, process_depth))
        
        # Sort processes: first by critical resources, then by depth (lower is closer to HV), then by score
        scored_processes.sort(key=lambda x: (x[2], -x[3] if x[3] > 0 else 0, x[1]), reverse=True)
        
        # Return process with highest score if score > 0, otherwise return None
        if scored_processes and scored_processes[0][1] > 0:
            return scored_processes[0][0]
        else:
            return None
