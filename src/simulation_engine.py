"""
Simulation Engine Core for Process Simulation

This module provides the SimulationEngine class that orchestrates the complete
simulation by integrating resource management, scheduling, and optimization.
"""

from typing import Dict, List, Optional, Tuple
from src.data_models import (
    SimulationConfig, SimulationResult, ProcessExecution,
    SimulationError, ResourceError
)
from src.resource_manager import ResourceManager
from src.scheduler import Scheduler
from src.optimizer_new import UniversalOptimizer as Optimizer
from src.common import Process
from src.performance_monitor import PerformanceMonitor, SimulationLimits


class SimulationEngine:
    """
    Core simulation engine that orchestrates the complete simulation.
    
    Responsibilities:
    - Manage the main simulation loop with cycle management
    - Coordinate resource manager, scheduler, and optimizer
    - Execute processes based on optimization strategies
    - Handle termination conditions
    - Generate simulation results
    """
    
    def __init__(self, config: SimulationConfig, limits: Optional[SimulationLimits] = None):
        """
        Initialize the simulation engine with configuration.
        
        Args:
            config: SimulationConfig object with simulation parameters
            limits: Optional performance limits and safeguards
        """
        self._config = config
        self._resource_manager = ResourceManager(config.initial_stocks)
        self._scheduler = Scheduler(initial_cycle=0)
        self._optimizer = Optimizer(config.optimization_targets, config.processes, config.max_delay)
        self._max_cycles = config.max_delay
        self._is_running = False
        self._termination_reason = ""
        self._performance_monitor = PerformanceMonitor(limits)
        self._enable_performance_monitoring = True
    
    def run(self) -> SimulationResult:
        """
        Run the complete simulation until termination.
        
        Returns:
            SimulationResult with execution history and final state
            
        Raises:
            SimulationError: If simulation encounters an unrecoverable error
        """
        self._is_running = True
        self._termination_reason = ""
        
        # Start performance monitoring
        if self._enable_performance_monitoring:
            self._performance_monitor.start_monitoring()
        
        try:
            # Main simulation loop
            while self._is_running:
                # Record cycle start for performance tracking
                if self._enable_performance_monitoring:
                    self._performance_monitor.record_cycle_start()
                
                # Check performance limits (excluding cycle limit which is handled separately)
                if self._enable_performance_monitoring:
                    execution_count = len(self._scheduler.get_execution_history())
                    limits = self._performance_monitor.get_limits()
                    
                    # Check execution limit
                    if execution_count >= limits.max_executions:
                        self._termination_reason = "execution_limit_exceeded"
                        raise SimulationError(f"Maximum execution limit exceeded: {limits.max_executions}")
                    
                    # Check memory limit
                    memory_mb = self._performance_monitor._get_memory_usage_mb()
                    if memory_mb > limits.max_memory_mb:
                        self._termination_reason = "memory_limit_exceeded"
                        raise SimulationError(f"Maximum memory limit exceeded: {memory_mb:.1f}MB > {limits.max_memory_mb}MB")
                
                # Check termination conditions
                if self._should_terminate():
                    break
                
                # Process any completing processes
                self._process_completions()
                
                # Try to start new processes
                self._execute_available_processes()
                
                # If no processes are active and none can start, terminate
                if not self._scheduler.has_active_processes():
                    if not self._can_execute_any_process():
                        self._termination_reason = "no_more_processes"
                        break
                
                # Advance to next event
                self._advance_to_next_event()
                
                # Record cycle end for performance tracking
                if self._enable_performance_monitoring:
                    self._performance_monitor.record_cycle_end(self._scheduler.get_current_cycle())
            
            # Complete all remaining in-progress processes
            while self._scheduler.has_active_processes():
                next_completion = self._scheduler.get_next_completion_cycle()
                if next_completion is not None:
                    self._scheduler.advance_cycle(next_completion - self._scheduler.get_current_cycle())
                    self._process_completions()
                else:
                    break
            
            # Stop performance monitoring
            if self._enable_performance_monitoring:
                self._performance_monitor.stop_monitoring()
            
            # Generate and return results
            return self._generate_result()
            
        except ResourceError as e:
            # Resource errors are expected and should be reported clearly
            raise SimulationError(
                f"Resource management error at cycle {self._scheduler.get_current_cycle()}: {e.message}",
                details={
                    'cycle': self._scheduler.get_current_cycle(),
                    'error_type': 'ResourceError',
                    'original_error': str(e)
                }
            )
        except Exception as e:
            # Unexpected errors should be wrapped with context
            raise SimulationError(
                f"Unexpected error during simulation at cycle {self._scheduler.get_current_cycle()}: {str(e)}",
                details={
                    'cycle': self._scheduler.get_current_cycle(),
                    'error_type': type(e).__name__,
                    'original_error': str(e)
                }
            )

    def _should_terminate(self) -> bool:
        """
        Check if simulation should terminate.
        
        Returns:
            True if termination condition is met
        """
        current_cycle = self._scheduler.get_current_cycle()
        
        # Check max cycle limit
        if current_cycle >= self._max_cycles:
            self._termination_reason = "max_cycles_reached"
            return True
        
        return False
    
    def _process_completions(self) -> None:
        """
        Process all completing processes at current cycle.
        Produces resources and records executions.
        """
        completing = self._scheduler.get_completing_processes()
        
        for scheduled in completing:
            process = scheduled.process
            current_cycle = self._scheduler.get_current_cycle()
            
            # Produce resources
            self._resource_manager.produce_resources(
                process.name,
                process.results,
                current_cycle
            )
            
            # Record execution
            self._scheduler.record_execution(
                process_name=process.name,
                start_cycle=scheduled.start_cycle,
                end_cycle=scheduled.end_cycle,
                resources_consumed=process.needs,
                resources_produced=process.results
            )
    
    def _execute_available_processes(self) -> None:
        """
        Execute all available processes that can run at current cycle.
        Uses optimizer to select best processes.
        """
        current_cycle = self._scheduler.get_current_cycle()
        current_stocks = self._resource_manager.get_all_stocks()
        
        # Track what we've executed this cycle to avoid infinite loops
        executed_this_cycle = set()
        
        # Keep trying to execute processes until none are available
        while True:
            # Find all executable processes
            executable = self._get_executable_processes()
            
            # Filter out processes we've already executed this cycle
            executable = [p for p in executable if p.name not in executed_this_cycle]
            
            if not executable:
                break
            
            # Select best process using optimizer
            best_process = self._optimizer.select_best_process(
                executable,
                current_stocks,
                current_cycle
            )
            
            if best_process is None:
                break
            
            # Execute the process
            try:
                self._execute_process(best_process)
                executed_this_cycle.add(best_process.name)
                
                # Record execution for performance tracking
                if self._enable_performance_monitoring:
                    self._performance_monitor.record_execution()
                
                # Update current stocks for next iteration
                current_stocks = self._resource_manager.get_all_stocks()
            except ResourceError:
                # Should not happen since we checked executability
                break
    
    def _get_executable_processes(self) -> List[Process]:
        """
        Get list of processes that can currently execute.
        
        Returns:
            List of executable Process objects
        """
        current_stocks = self._resource_manager.get_all_stocks()
        executable = []
        
        for process in self._config.processes:
            if self._resource_manager.has_sufficient_resources(process.needs):
                executable.append(process)
        
        return executable
    
    def _can_execute_any_process(self) -> bool:
        """
        Check if any process can be executed with current resources.
        
        Returns:
            True if at least one process can execute
        """
        return len(self._get_executable_processes()) > 0
    
    def _execute_process(self, process: Process) -> None:
        """
        Execute a single process: consume resources and schedule.
        
        Args:
            process: The process to execute
            
        Raises:
            ResourceError: If insufficient resources
            SimulationError: If process execution fails
        """
        if process is None:
            raise SimulationError("Cannot execute None process")
        
        current_cycle = self._scheduler.get_current_cycle()
        
        try:
            # Consume resources
            self._resource_manager.consume_resources(
                process.name,
                process.needs,
                current_cycle
            )
            
            # Schedule the process
            self._scheduler.schedule_process(
                process,
                resources_consumed=process.needs,
                resources_to_produce=process.results
            )
        except ResourceError:
            # Re-raise resource errors as-is
            raise
        except Exception as e:
            # Wrap other errors with context
            raise SimulationError(
                f"Failed to execute process '{process.name}' at cycle {current_cycle}: {str(e)}",
                details={
                    'cycle': current_cycle,
                    'process': process.name,
                    'error_type': type(e).__name__
                }
            )
    
    def _advance_to_next_event(self) -> None:
        """
        Advance simulation to the next event (process completion or max cycles).
        """
        # If there are active processes, advance to next completion
        next_completion = self._scheduler.get_next_completion_cycle()
        
        if next_completion is not None:
            current_cycle = self._scheduler.get_current_cycle()
            cycles_to_advance = next_completion - current_cycle
            
            if cycles_to_advance > 0:
                # Don't advance past max_cycles
                if current_cycle + cycles_to_advance > self._max_cycles:
                    cycles_to_advance = self._max_cycles - current_cycle
                
                if cycles_to_advance > 0:
                    self._scheduler.advance_cycle(cycles_to_advance)
        else:
            # No active processes, simulation should terminate
            self._is_running = False
    
    def _generate_result(self) -> SimulationResult:
        """
        Generate final simulation result.
        
        Returns:
            SimulationResult with complete simulation data
        """
        return SimulationResult(
            executions=self._scheduler.get_execution_history(),
            final_stocks=self._resource_manager.get_all_stocks(),
            final_cycle=self._scheduler.get_current_cycle(),
            termination_reason=self._termination_reason
        )
    
    def get_current_cycle(self) -> int:
        """Get current simulation cycle"""
        return self._scheduler.get_current_cycle()
    
    def get_current_stocks(self) -> Dict[str, int]:
        """Get current resource stocks"""
        return self._resource_manager.get_all_stocks()
    
    def get_execution_history(self) -> List[ProcessExecution]:
        """Get execution history so far"""
        return self._scheduler.get_execution_history()
    
    def is_running(self) -> bool:
        """Check if simulation is currently running"""
        return self._is_running
    
    def reset(self) -> None:
        """Reset the simulation engine to initial state"""
        self._resource_manager.reset()
        self._scheduler.reset()
        self._is_running = False
        self._termination_reason = ""
        self._performance_monitor = PerformanceMonitor(self._performance_monitor.get_limits())
    
    def get_performance_metrics(self):
        """Get performance metrics from the monitor"""
        return self._performance_monitor.get_metrics()
    
    def get_performance_summary(self) -> Dict:
        """Get performance summary as dictionary"""
        return self._performance_monitor.get_summary()
    
    def print_performance_summary(self) -> None:
        """Print performance summary to console"""
        self._performance_monitor.print_summary()
    
    def set_performance_monitoring(self, enabled: bool) -> None:
        """Enable or disable performance monitoring"""
        self._enable_performance_monitoring = enabled
    
    def __str__(self) -> str:
        """String representation of engine state"""
        return (f"SimulationEngine(cycle={self.get_current_cycle()}, "
                f"running={self._is_running}, "
                f"executions={len(self.get_execution_history())})")
    
    def __repr__(self) -> str:
        return self.__str__()
