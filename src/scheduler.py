from dataclasses import dataclass
from typing import Dict, List, Optional, Set

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
    def __init__(self, initial_cycle: int = 0, max_history: int = 100000):
        self._current_cycle: int = initial_cycle
        self._scheduled_processes: List[ScheduledProcess] = []
        self._execution_history: List[ProcessExecution] = []
        self._process_start_times: Dict[str, List[int]] = {}
        self._process_completion_times: Dict[str, List[int]] = {}
        self._max_history = max_history
    
    def get_current_cycle(self) -> int:
        return self._current_cycle
    
    def advance_cycle(self, cycles: int = 1) -> int:
        if cycles < 0:
            raise ValueError(f"Cannot advance by negative cycles: {cycles}")
        
        self._current_cycle += cycles
        return self._current_cycle
    
    def schedule_process(self, process: Process) -> ScheduledProcess:
        if not process:
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
        
        if process.name not in self._process_start_times:
            self._process_start_times[process.name] = []
        self._process_start_times[process.name].append(start_cycle)
        process.record_execution(start_cycle)
        return scheduled
    
    def get_completing_processes(self) -> List[ScheduledProcess]:
        completing = []
        remaining = []
        
        for scheduled in self._scheduled_processes:
            if scheduled.is_complete(self._current_cycle):
                completing.append(scheduled)
                process_name = scheduled.process.name
                if process_name not in self._process_completion_times:
                    self._process_completion_times[process_name] = []
                self._process_completion_times[process_name].append(self._current_cycle)
            else:
                remaining.append(scheduled)
        
        self._scheduled_processes = remaining
        return completing
    
    def has_active_processes(self) -> bool:
        return len(self._scheduled_processes) > 0
    
    def get_next_completion_cycle(self) -> Optional[int]:
        return min(sp.end_cycle for sp in self._scheduled_processes) if self._scheduled_processes else None
    
    def record_execution(self,
                        process_name: str,
                        start_cycle: int,
                        end_cycle: int,
                        resources_consumed: Dict[str, int],
                        resources_produced: Dict[str, int]) -> ProcessExecution:
        execution = ProcessExecution(
            process_name=process_name,
            start_cycle=start_cycle,
            end_cycle=end_cycle,
            resources_consumed=resources_consumed,
            resources_produced=resources_produced
        )
        
        self._execution_history.append(execution)
        if self._max_history > 0 and len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
        
        return execution
    
    def get_execution_history(self) -> List[ProcessExecution]:
        return self._execution_history.copy()
