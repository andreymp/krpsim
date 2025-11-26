from typing import List

from src.data_models import SimulationConfig, SimulationResult, SimulationError, ResourceError
from src.resource_manager import ResourceManager
from src.scheduler import Scheduler
from src.optimizer import Optimizer
from src.common import Process

class SimulationEngine:
    def __init__(self, config: SimulationConfig):
        self._config = config
        self._resource_manager = ResourceManager(config.initial_stocks)
        self._scheduler = Scheduler(initial_cycle=0)
        self._optimizer = Optimizer(config.optimization_targets, config.processes, config.max_delay)
        self._max_cycles = config.max_delay
        self._is_running = False
        self._termination_reason = ""
    
    def run(self) -> SimulationResult:
        self._is_running = True
        self._termination_reason = ""
        try:
            while self._is_running:
                if self._should_terminate():
                    break
                
                self._process_completions()
                self._execute_available_processes()
                
                if not self._scheduler.has_active_processes() and not self._can_execute_any_process():
                    self._termination_reason = "no_more_processes"
                    break
                
                self._advance_to_next_event()            
            while self._scheduler.has_active_processes():
                next_completion = self._scheduler.get_next_completion_cycle()
                if next_completion:
                    self._scheduler.advance_cycle(next_completion - self._scheduler.get_current_cycle())
                    self._process_completions()
                else:
                    break
            return self._generate_result()
            
        except ResourceError as e:
            raise SimulationError(
                f"Resource management error at cycle {self._scheduler.get_current_cycle()}: {e.message}",
                details={
                    'cycle': self._scheduler.get_current_cycle(),
                    'error_type': 'ResourceError',
                    'original_error': str(e)
                }
            )
        except Exception as e:
            raise SimulationError(
                f"Unexpected error during simulation at cycle {self._scheduler.get_current_cycle()}: {str(e)}",
                details={
                    'cycle': self._scheduler.get_current_cycle(),
                    'error_type': type(e).__name__,
                    'original_error': str(e)
                }
            )

    def _should_terminate(self) -> bool:
        current_cycle = self._scheduler.get_current_cycle()
        if current_cycle >= self._max_cycles:
            self._termination_reason = "max_cycles_reached"
            return True
        return False
    
    def _process_completions(self) -> None:
        completing = self._scheduler.get_completing_processes()
        for scheduled in completing:
            process = scheduled.process
            current_cycle = self._scheduler.get_current_cycle()
            self._resource_manager.produce_resources(
                process.name,
                process.results,
                current_cycle
            )
            self._scheduler.record_execution(
                process_name=process.name,
                start_cycle=scheduled.start_cycle,
                end_cycle=scheduled.end_cycle,
                resources_consumed=process.needs,
                resources_produced=process.results
            )
    
    def _execute_available_processes(self) -> None:
        current_cycle = self._scheduler.get_current_cycle()
        current_stocks = self._resource_manager.get_all_stocks()
        executed_this_cycle = set()
        while True:
            executable = [
                process 
                for process in self._get_executable_processes()
                if process.name not in executed_this_cycle
            ]
            if not executable:
                break
            
            best_process = self._optimizer.select_best_process(
                executable,
                current_stocks,
                current_cycle
            )
            if best_process is None:
                break
            
            try:
                self._execute_process(best_process)
                executed_this_cycle.add(best_process.name)
                
                current_stocks = self._resource_manager.get_all_stocks()
            except ResourceError:
                break
    
    def _get_executable_processes(self) -> List[Process]:
        return [
            process 
            for process in self._config.processes 
            if self._resource_manager.has_sufficient_resources(process.needs)
        ]
    
    def _can_execute_any_process(self) -> bool:
        return len(self._get_executable_processes()) > 0
    
    def _execute_process(self, process: Process) -> None:
        if not process:
            raise SimulationError("Cannot execute None process")
        
        current_cycle = self._scheduler.get_current_cycle()
        try:
            self._resource_manager.consume_resources(
                process.name,
                process.needs,
                current_cycle
            )
            self._scheduler.schedule_process(process)
        except ResourceError:
            raise
        except Exception as e:
            raise SimulationError(
                f"Failed to execute process '{process.name}' at cycle {current_cycle}: {str(e)}",
                details={
                    'cycle': current_cycle,
                    'process': process.name,
                    'error_type': type(e).__name__
                }
            )
    
    def _advance_to_next_event(self) -> None:
        next_completion = self._scheduler.get_next_completion_cycle()
        if next_completion:
            current_cycle = self._scheduler.get_current_cycle()
            cycles_to_advance = next_completion - current_cycle
            
            if cycles_to_advance > 0:
                if current_cycle + cycles_to_advance > self._max_cycles:
                    cycles_to_advance = self._max_cycles - current_cycle
                
                if cycles_to_advance > 0:
                    self._scheduler.advance_cycle(cycles_to_advance)
        else:
            self._is_running = False
    
    def _generate_result(self) -> SimulationResult:
        return SimulationResult(
            executions=self._scheduler.get_execution_history(),
            final_stocks=self._resource_manager.get_all_stocks(),
            final_cycle=self._scheduler.get_current_cycle(),
            termination_reason=self._termination_reason
        )
