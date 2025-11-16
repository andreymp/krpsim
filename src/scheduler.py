"""
Discrete Event Scheduler for Process Simulation

This module provides the Scheduler class for managing cycle-based simulation
with process scheduling, delay handling, and execution tracking.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from src.common import Process
from src.data_models import ProcessExecution, SchedulingError


@dataclass
class ScheduledProcess:
    """Represents a process scheduled for execution"""
    process: Process
    start_cycle: int
    end_cycle: int
    
    def is_complete(self, current_cycle: int) -> bool:
        """Check if this scheduled process has completed"""
        return current_cycle >= self.end_cycle
    
    def __str__(self) -> str:
        return f"ScheduledProcess({self.process.name}, start={self.start_cycle}, end={self.end_cycle})"
    
    def __repr__(self) -> str:
        return self.__str__()


class Scheduler:
    """
    Manages cycle-based simulation scheduling with delay handling.
    
    Responsibilities:
    - Track current simulation cycle
    - Schedule processes for execution with delays
    - Track when processes start and complete
    - Manage process execution history
    - Determine when processes complete and resources should be produced
    """
    
    def __init__(self, initial_cycle: int = 0, max_history: int = 100000):
        """
        Initialize the scheduler.
        
        Args:
            initial_cycle: Starting cycle for the simulation (default: 0)
            max_history: Maximum number of executions to keep in history
        """
        self._current_cycle: int = initial_cycle
        self._scheduled_processes: List[ScheduledProcess] = []
        self._execution_history: List[ProcessExecution] = []
        self._process_start_times: Dict[str, List[int]] = {}
        self._process_completion_times: Dict[str, List[int]] = {}
        self._max_history = max_history
    
    def get_current_cycle(self) -> int:
        """Get the current simulation cycle"""
        return self._current_cycle
    
    def advance_cycle(self, cycles: int = 1) -> int:
        """
        Advance the simulation by the specified number of cycles.
        
        Args:
            cycles: Number of cycles to advance (default: 1)
            
        Returns:
            The new current cycle
            
        Raises:
            ValueError: If cycles is negative
        """
        if cycles < 0:
            raise ValueError(f"Cannot advance by negative cycles: {cycles}")
        
        self._current_cycle += cycles
        return self._current_cycle
    
    def schedule_process(self, 
                        process: Process, 
                        resources_consumed: Dict[str, int],
                        resources_to_produce: Dict[str, int]) -> ScheduledProcess:
        """
        Schedule a process for execution starting at the current cycle.
        
        Args:
            process: The process to schedule
            resources_consumed: Resources consumed at start
            resources_to_produce: Resources to be produced at completion
            
        Returns:
            ScheduledProcess object representing the scheduled execution
            
        Raises:
            SchedulingError: If process or parameters are invalid
        """
        # Validate process
        if process is None:
            raise SchedulingError(
                "Cannot schedule None process",
                cycle=self._current_cycle
            )
        
        if not process.name:
            raise SchedulingError(
                "Process name cannot be empty",
                cycle=self._current_cycle
            )
        
        if process.delay <= 0:
            raise SchedulingError(
                f"Process delay must be positive: {process.delay}",
                cycle=self._current_cycle,
                process_name=process.name
            )
        
        start_cycle = self._current_cycle
        end_cycle = start_cycle + process.delay
        
        scheduled = ScheduledProcess(
            process=process,
            start_cycle=start_cycle,
            end_cycle=end_cycle
        )
        
        self._scheduled_processes.append(scheduled)
        
        # Track start time
        if process.name not in self._process_start_times:
            self._process_start_times[process.name] = []
        self._process_start_times[process.name].append(start_cycle)
        
        # Record execution in process
        process.record_execution(start_cycle)
        
        return scheduled
    
    def get_completing_processes(self) -> List[ScheduledProcess]:
        """
        Get all processes that complete at the current cycle.
        
        Returns:
            List of ScheduledProcess objects completing this cycle
        """
        completing = []
        remaining = []
        
        for scheduled in self._scheduled_processes:
            if scheduled.is_complete(self._current_cycle):
                completing.append(scheduled)
                
                # Track completion time
                process_name = scheduled.process.name
                if process_name not in self._process_completion_times:
                    self._process_completion_times[process_name] = []
                self._process_completion_times[process_name].append(self._current_cycle)
            else:
                remaining.append(scheduled)
        
        # Update scheduled processes list to only include remaining
        self._scheduled_processes = remaining
        
        return completing
    
    def get_active_processes(self) -> List[ScheduledProcess]:
        """
        Get all currently scheduled (active) processes.
        
        Returns:
            List of ScheduledProcess objects that are currently running
        """
        return self._scheduled_processes.copy()
    
    def has_active_processes(self) -> bool:
        """
        Check if there are any active scheduled processes.
        
        Returns:
            True if there are processes currently scheduled
        """
        return len(self._scheduled_processes) > 0
    
    def get_next_completion_cycle(self) -> Optional[int]:
        """
        Get the cycle when the next process will complete.
        
        Returns:
            Cycle number of next completion, or None if no processes are scheduled
        """
        if not self._scheduled_processes:
            return None
        
        return min(sp.end_cycle for sp in self._scheduled_processes)
    
    def record_execution(self,
                        process_name: str,
                        start_cycle: int,
                        end_cycle: int,
                        resources_consumed: Dict[str, int],
                        resources_produced: Dict[str, int]) -> ProcessExecution:
        """
        Record a completed process execution.
        
        Args:
            process_name: Name of the process
            start_cycle: Cycle when process started
            end_cycle: Cycle when process completed
            resources_consumed: Resources consumed at start
            resources_produced: Resources produced at completion
            
        Returns:
            ProcessExecution object representing the completed execution
        """
        execution = ProcessExecution(
            process_name=process_name,
            start_cycle=start_cycle,
            end_cycle=end_cycle,
            resources_consumed=resources_consumed,
            resources_produced=resources_produced
        )
        
        self._execution_history.append(execution)
        
        # Prune history if it gets too large
        if self._max_history > 0 and len(self._execution_history) > self._max_history:
            # Keep only the most recent executions
            self._execution_history = self._execution_history[-self._max_history:]
        
        return execution
    
    def get_execution_history(self) -> List[ProcessExecution]:
        """
        Get the complete execution history.
        
        Returns:
            List of all ProcessExecution records in chronological order
        """
        return self._execution_history.copy()
    
    def get_process_start_times(self, process_name: str) -> List[int]:
        """
        Get all start times for a specific process.
        
        Args:
            process_name: Name of the process
            
        Returns:
            List of cycle numbers when the process was started
        """
        return self._process_start_times.get(process_name, []).copy()
    
    def get_process_completion_times(self, process_name: str) -> List[int]:
        """
        Get all completion times for a specific process.
        
        Args:
            process_name: Name of the process
            
        Returns:
            List of cycle numbers when the process completed
        """
        return self._process_completion_times.get(process_name, []).copy()
    
    def get_all_process_names(self) -> Set[str]:
        """
        Get names of all processes that have been scheduled.
        
        Returns:
            Set of process names
        """
        return set(self._process_start_times.keys())
    
    def reset(self) -> None:
        """
        Reset the scheduler to initial state.
        Clears all scheduled processes and execution history.
        """
        self._current_cycle = 0
        self._scheduled_processes.clear()
        self._execution_history.clear()
        self._process_start_times.clear()
        self._process_completion_times.clear()
    
    def __str__(self) -> str:
        """String representation of scheduler state"""
        return (f"Scheduler(cycle={self._current_cycle}, "
                f"active={len(self._scheduled_processes)}, "
                f"completed={len(self._execution_history)})")
    
    def __repr__(self) -> str:
        return self.__str__()
