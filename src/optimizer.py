import math
from typing import Dict, List, Optional, Set, Tuple
from src.common import Process

class Optimizer:
    def __init__(self, optimization_targets: List[str], all_processes: Optional[List[Process]] = None, total_cycles: int = 0):
        self.optimization_targets = [target for target in optimization_targets if target != 'time']
        self.total_cycles = total_cycles
        self.high_value_processes: Set[str] = set()
        self.value_chain_resources: Set[str] = set()
        self.resource_needs: Dict[str, Dict[str, int]] = {}
        self.resource_depths: Dict[str, int] = {}
        self.bulk_targets: Dict[str, int] = {}
        self.target_reserves: Dict[str, int] = {}
        self.current_phase = "gather"
        self.is_analyzed = False
        self.known_processes: List[Process] = all_processes or []
        self.reserve_multiplier = max(1.0, math.log10(max(total_cycles, 1000)) - 2.0)
        
        if self.known_processes:
            self._analyze(self.known_processes)
    
    def _identify_high_value_processes(self, processes: List[Process]) -> None:
        max_net_production = {
            target: max((proc.results.get(target, 0) - proc.needs.get(target, 0) 
                        for proc in processes if target in proc.results), default=0) 
            for target in self.optimization_targets
        }
        for proc in processes:
            for target in self.optimization_targets:
                if target in proc.results:
                    net_production = proc.results[target] - proc.needs.get(target, 0)
                    if (net_production > 1000 
                        or (proc.needs.get(target, 0) > 0 and net_production > 50 * proc.needs[target]) 
                        or proc.results[target] > 10000 
                        or (max_net_production[target] > 0 and net_production >= max_net_production[target] * 0.5)
                    ):
                        self.high_value_processes.add(proc.name)
                        for resource_name, quantity in proc.needs.items():
                            if resource_name not in self.optimization_targets:
                                self.resource_needs.setdefault(proc.name, {})[resource_name] = quantity
                        break
    
    def _build_dependency_graph(self, processes: List[Process]) -> None:
        for proc in processes:
            if proc.name in self.high_value_processes:
                self._deps(proc, processes, set())
        for proc in processes:
            if any(result in self.value_chain_resources for result in proc.results) and proc.name not in self.high_value_processes:
                if not self._is_conversion_loop(proc, processes):
                    for resource_name, quantity in proc.needs.items():
                        if resource_name not in self.optimization_targets:
                            self.resource_needs.setdefault(proc.name, {})[resource_name] = quantity
    
    def _is_conversion_loop(self, process: Process, all_processes: List[Process]) -> bool:
        for result_resource in process.results:
            for need_resource in process.needs:
                for other_proc in all_processes:
                    if (other_proc.name != process.name 
                        and need_resource in other_proc.results 
                        and result_resource in other_proc.needs):
                        return True
        return False
    
    def _calculate_resource_depths(self, processes: List[Process]) -> None:
        for hv_process_name in self.high_value_processes:
            for proc in processes:
                if proc.name == hv_process_name:
                    for resource in proc.needs:
                        if resource not in self.optimization_targets:
                            self.resource_depths[resource] = min(
                                self.resource_depths.get(resource, 999), 
                                1
                            )
        for _ in range(10):
            for proc in processes:
                for result_resource in proc.results:
                    if result_resource in self.resource_depths:
                        for need_resource in proc.needs:
                            if need_resource not in self.optimization_targets:
                                self.resource_depths[need_resource] = min(
                                    self.resource_depths.get(need_resource, 999), 
                                    self.resource_depths[result_resource] + 1
                                )
    
    def _determine_bulk_targets(self, processes: List[Process]) -> None:
        max_hv_production = max((proc.results.get(target, 0) 
                                for proc in processes 
                                for target in self.optimization_targets 
                                if proc.name in self.high_value_processes), default=0)
        bulk_multiplier = (20 if max_hv_production >= 10000 
                          else (10 if max_hv_production >= 1000 
                          else (5 if max_hv_production >= 100 
                          else 2)))

        for hv_process_name in self.high_value_processes:
            for proc in processes:
                if proc.name == hv_process_name:
                    for resource, quantity in proc.needs.items():
                        if resource not in self.optimization_targets:
                            self.bulk_targets[resource] = max(
                                self.bulk_targets.get(resource, 0), 
                                quantity * bulk_multiplier
                            )
        for _ in range(2):
            for resource in list(self.bulk_targets.keys()):
                for proc in processes:
                    if resource in proc.results:
                        runs_needed = (self.bulk_targets[resource] + proc.results[resource] - 1) // proc.results[resource]
                        for need_resource, need_quantity in proc.needs.items():
                            if need_resource not in self.optimization_targets:
                                self.bulk_targets[need_resource] = max(
                                    self.bulk_targets.get(need_resource, 0), 
                                    int(need_quantity * runs_needed * 0.5)
                                )
    
    def _calculate_reserves(self, processes: List[Process]) -> None:
        for proc in processes:
            if proc.name in self.high_value_processes or proc.name in self.resource_needs:
                for target in self.optimization_targets:
                    if target in proc.needs:
                        multiplier = (100 if proc.name in self.high_value_processes 
                                     else 500)
                        self.target_reserves[target] = max(
                            self.target_reserves.get(target, 0), 
                            int(proc.needs[target] * multiplier * self.reserve_multiplier)
                        )
    
    def _analyze(self, processes: List[Process]) -> None:
        if self.is_analyzed or not self.optimization_targets:
            return
    
        self._identify_high_value_processes(processes)
        self._build_dependency_graph(processes)
        self._calculate_resource_depths(processes)
        self._determine_bulk_targets(processes)
        self._calculate_reserves(processes)
        
        self.is_analyzed = True
    
    def _deps(self, process: Process, all_processes: List[Process], visited: Set[str]) -> None:
        for needed_resource in process.needs:
            if needed_resource not in visited:
                self.value_chain_resources.add(needed_resource)
                visited.add(needed_resource)
                for producer_process in all_processes:
                    if needed_resource in producer_process.results:
                        self._deps(producer_process, all_processes, visited)
    
    def _determine_phase(self, stocks: Dict[str, int], cycle: int) -> str:
        if not self.is_analyzed:
            return "gather"
        if self.total_cycles > 0 and cycle >= int(self.total_cycles * 0.7):
            return "sell"
        
        can_execute_hv = any(
            all(stocks.get(resource, 0) >= quantity for resource, quantity in proc.needs.items()) 
            for hv_name in self.high_value_processes 
            for proc in self.known_processes 
            if proc.name == hv_name
        )
        if can_execute_hv:
            return "sell"
        
        value_chain_stock = sum(stocks.get(resource, 0) 
                               for resource in self.value_chain_resources 
                               if resource not in self.optimization_targets)
        value_chain_need = sum(self.resource_needs[hv_name].get(resource, 0) * 10 
                              for hv_name in self.high_value_processes 
                              for resource in self.resource_needs.get(hv_name, {}))
        phase_convert_min_cycle = max(100, int(self.total_cycles * 0.1)) if self.total_cycles > 0 else 1000
        phase_build_min_cycle = max(50, int(self.total_cycles * 0.05)) if self.total_cycles > 0 else 500
        
        if cycle > phase_convert_min_cycle or (value_chain_need > 0 and value_chain_stock > value_chain_need * 0.2):
            return "convert"
        
        if cycle > phase_build_min_cycle or (value_chain_need > 0 and value_chain_stock > value_chain_need * 0.02):
            return "build"
        
        return "gather"
    
    def _get_phase_adjusted_reserve(self, target_resource: str) -> int:
        base_reserve = self.target_reserves.get(target_resource, 0)
        phase_multiplier = (0.001 if self.current_phase == "gather" 
                          else (0.1 if self.current_phase == "build" 
                          else (0.5 if self.current_phase == "convert" 
                          else 1.0)))
        return int(base_reserve * phase_multiplier)
    
    def _build_resource_to_process_map(self, available: List[Process]) -> Dict[str, List[Process]]:
        resource_to_process_map = {}
        for process in available:
            for resource in process.results:
                resource_to_process_map.setdefault(resource, []).append(process)
        return resource_to_process_map
    
    def _get_bulk_multiplier(self) -> int:
        max_hv_production = max((proc.results.get(target, 0) 
                                for proc in self.known_processes 
                                for target in self.optimization_targets 
                                if proc.name in self.high_value_processes), default=0)
        
        if max_hv_production >= 10000:
            return 20
        elif max_hv_production >= 1000:
            return 10
        elif max_hv_production >= 100:
            return 5
        else:
            return 2
    
    def _is_gathering_process(self, process: Process) -> bool:
        return (len(process.needs) <= 1 and 
                any(target in process.needs for target in self.optimization_targets))
    
    def _get_reserve_multiplier(self, process: Process) -> float:
        return (100 if process.name in self.high_value_processes 
                else 500) * self.reserve_multiplier
    
    def _identify_bottlenecks(self, available: List[Process], stocks: Dict[str, int]) -> List[Tuple[Process, float]]:
        bottlenecks = []
        resource_to_process_map = self._build_resource_to_process_map(available)
        
        for process_name in self.resource_needs:
            for resource, quantity in self.resource_needs[process_name].items():
                current_stock = stocks.get(resource, 0)
                buffer_multiplier = (100 if process_name in self.high_value_processes 
                                    else 50)
                
                if current_stock < quantity * buffer_multiplier and resource in resource_to_process_map:
                    base_urgency = 1000000.0 if process_name in self.high_value_processes else 500000.0
                    shortage = quantity * buffer_multiplier - current_stock
                    
                    for process in resource_to_process_map[resource]:
                        bottlenecks.append((process, base_urgency + shortage * 1000.0))
        
        for resource in self.value_chain_resources:
            current_stock = stocks.get(resource, 0)
            bulk_target = self.bulk_targets.get(resource, 0)
            if bulk_target > 0 and current_stock < bulk_target and resource in resource_to_process_map:
                shortage = bulk_target - current_stock
                for process in resource_to_process_map[resource]:
                    bottlenecks.append((process, shortage * 1000.0))
            elif current_stock < 10 and resource in resource_to_process_map:
                shortage = 10 - current_stock
                for process in resource_to_process_map[resource]:
                    bottlenecks.append((process, shortage * 1000.0))
        
        if self.current_phase in ["convert", "sell"]:
            bulk_multiplier = self._get_bulk_multiplier()
            for hv_process_name in self.high_value_processes:
                for proc in self.known_processes:
                    if proc.name == hv_process_name:
                        for resource, quantity in proc.needs.items():
                            current_stock = stocks.get(resource, 0)
                            needed_amount = quantity * bulk_multiplier
                            
                            if current_stock < needed_amount and resource in resource_to_process_map:
                                shortage = needed_amount - current_stock
                                for producer_process in resource_to_process_map[resource]:
                                    bottlenecks.append((producer_process, 10000000.0 + shortage * 10000.0))
        
        return bottlenecks
    
    def _apply_target_bonuses(self, process: Process, stocks: Dict[str, int], score: float) -> float:
        for target in self.optimization_targets:
            if target in process.results:
                net_production = process.results[target] - process.needs.get(target, 0)
                critical_bulk_shortage = any(
                    resource in self.bulk_targets 
                    and stocks.get(resource, 0) < self.bulk_targets[resource] * 0.5 
                    and stocks.get(resource, 0) < process.needs[resource] * 2 
                    for resource in process.needs 
                    if resource in self.bulk_targets
                )
                
                if critical_bulk_shortage:
                    targets_are_low = any(stocks.get(t, 0) < self._get_phase_adjusted_reserve(t) 
                                        for t in self.optimization_targets)
                    score *= 1.0 if (targets_are_low and net_production > 0) else 0.0001
                else:
                    if process.name not in self.high_value_processes and len(self.high_value_processes) > 0:
                        scale_multiplier = (20.0 if net_production > 10000 
                                          else (8.0 if net_production > 1000 
                                          else (3.0 if net_production > 100 
                                          else (1.0 if net_production > 0 else 1.0))))
                        bonus = net_production * 5000.0 * scale_multiplier
                    else:
                        scale_multiplier = (200.0 if net_production > 10000 
                                          else (80.0 if net_production > 1000 
                                          else (30.0 if net_production > 100 
                                          else (10.0 if net_production > 0 else 10.0))))
                        bonus = net_production * 50000.0 * scale_multiplier
                    score += bonus
        
        return score
    
    def _apply_high_value_multipliers(self, process: Process, stocks: Dict[str, int], score: float) -> float:
        if process.name in self.high_value_processes:
            bulk_multiplier = self._get_bulk_multiplier()
            can_bulk_execute = all(stocks.get(resource, 0) >= quantity * bulk_multiplier 
                                  for resource, quantity in process.needs.items())
            can_execute = all(stocks.get(resource, 0) >= quantity 
                             for resource, quantity in process.needs.items())
            
            if can_bulk_execute:
                score *= 100000000.0 if self.current_phase in ["convert", "sell"] else 10000000.0
            elif can_execute:
                score *= 10000000.0 if self.current_phase in ["convert", "sell"] else 1000.0
        return score
    
    def _apply_bulk_target_multipliers(self, process: Process, stocks: Dict[str, int], score: float) -> float:
        is_conversion_loop = self._is_conversion_loop(process, self.known_processes)
        
        if not is_conversion_loop:
            for resource in process.results:
                if resource in self.bulk_targets:
                    current_stock = stocks.get(resource, 0)
                    target_stock = self.bulk_targets[resource]
                    
                    if current_stock < target_stock:
                        shortage_ratio = (target_stock - current_stock) / target_stock
                        score *= (1000.0 + shortage_ratio * 100000.0)
                    else:
                        score *= 0.0001
        
        return score
    
    def _apply_target_consumption_penalties(self, process: Process, stocks: Dict[str, int], score: float) -> float:
        is_gathering_process = self._is_gathering_process(process)
        for target in self.optimization_targets:
            if target in process.needs:
                consumption = process.needs[target]
                available_after_reserve = stocks.get(target, 0) - self._get_phase_adjusted_reserve(target)
                
                if available_after_reserve < consumption:
                    if process.name in self.high_value_processes:
                        penalty = 1.0
                    elif is_gathering_process:
                        penalty = 10000000.0
                    elif process.name in self.resource_needs:
                        penalty = 10000000.0
                    else:
                        penalty = 10000000.0
                    score -= consumption * penalty
                else:
                    scarcity_multiplier = (10000.0 if available_after_reserve < 100 
                                         else (1000.0 if available_after_reserve < 1000 
                                         else 100.0))
                    process_multiplier = 0.1 if process.name in self.resource_needs else 1.0
                    penalty = scarcity_multiplier * process_multiplier
                    score -= consumption * penalty
        
        return score
    
    def _apply_phase_multipliers(self, process: Process, stocks: Dict[str, int], score: float) -> float:
        is_gathering_process = self._is_gathering_process(process)
        
        if self.current_phase == "gather":
            score *= 2.0 if is_gathering_process else 1.0
            
        elif self.current_phase == "build":
            if is_gathering_process:
                score *= 0.0001
            elif any(self.resource_depths.get(resource, 0) >= 2 for resource in process.results):
                score *= 50.0
                
        elif self.current_phase == "convert":
            if is_gathering_process:
                score *= 0.000001
            else:
                for resource in process.results:
                    depth = self.resource_depths.get(resource, 0)
                    if depth == 1:
                        score *= self.SCORE_PHASE_CONVERT_DEPTH_1
                        break
                    elif depth == 2:
                        score *= self.SCORE_PHASE_CONVERT_DEPTH_2
                        break
                        
        elif self.current_phase == "sell":
            if is_gathering_process:
                score *= 0.00000001
            elif process.name not in self.high_value_processes:
                score *= 0.01
        
        for resource in process.results:
            if resource in self.value_chain_resources:
                current_stock = stocks.get(resource, 0)
                score *= (5.0 if current_stock == 0 
                        else (3.0 if current_stock < 10 
                        else (2.0 if current_stock < 30 
                        else 1.0)))
        
        for resource in process.results:
            if resource in process.needs:
                score *= 0.0001
        
        return score
    
    def _calculate_process_score(self, process: Process, stocks: Dict[str, int]) -> Tuple[float, bool, int]:
        input_cost = sum(process.needs.values())
        output_value = sum(process.results.values())
        
        if not process.needs:
            score = 100000.0
        else:
            score = (output_value / input_cost) * 100.0 if input_cost > 0 else output_value * 100.0
        
        score = self._apply_target_bonuses(process, stocks, score)
        score = self._apply_high_value_multipliers(process, stocks, score)
        score = self._apply_bulk_target_multipliers(process, stocks, score)
        score = self._apply_target_consumption_penalties(process, stocks, score)
        score = self._apply_phase_multipliers(process, stocks, score)
        
        score -= process.delay + process.execution_count * 0.1
        
        min_depth = min((self.resource_depths.get(resource, 999) 
                       for resource in process.results 
                       if resource in self.resource_depths), default=0)
        is_critical = any(resource in self.resource_depths for resource in process.results)

        return score, is_critical, min_depth
    
    def select_best_process(self, available: List[Process], stocks: Dict[str, int], cycle: int) -> Optional[Process]:
        if not available:
            return None
        
        if not self.is_analyzed:
            for process in available:
                if process not in self.known_processes:
                    self.known_processes.append(process)
            if len(self.known_processes) > 10:
                self._analyze(self.known_processes)

        if self.is_analyzed:
            self.current_phase = self._determine_phase(stocks, cycle)
        
        bottlenecks = self._identify_bottlenecks(available, stocks)
        
        if bottlenecks:
            affordable_bottlenecks = []
            for process, urgency in bottlenecks:
                is_affordable = True
                is_gathering = self._is_gathering_process(process)
                if is_gathering and self.current_phase != "gather":
                    for target in self.optimization_targets:
                        if target in process.needs:
                            available_after_reserve = stocks.get(target, 0) - self._get_phase_adjusted_reserve(target)
                            if available_after_reserve < process.needs[target]:
                                is_affordable = False
                                break
                
                if is_affordable:
                    affordable_bottlenecks.append((process, urgency))
 
            if affordable_bottlenecks:
                return max(affordable_bottlenecks, key=lambda x: x[1])[0]
        
        scored_processes = []
        for process in available:
            score, is_critical, min_depth = self._calculate_process_score(process, stocks)
            scored_processes.append((process, score, is_critical, min_depth))
        
        positive_scores = [(proc, score, is_crit, depth) 
                          for proc, score, is_crit, depth in scored_processes 
                          if score > 0]
        
        if not positive_scores:
            return None

        return max(positive_scores, key=lambda x: (x[2], -x[3] if x[3] > 0 else 0, x[1]))[0]
