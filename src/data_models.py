from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING, Any
from enum import Enum

if TYPE_CHECKING:
    from src.common import Process


@dataclass
class SimulationConfig:
    initial_stocks: Dict[str, int]
    processes: List['Process']
    optimization_targets: List[str]
    max_delay: int
    config_file: Optional[str] = None
    
    def __post_init__(self):
        if self.max_delay <= 0:
            raise ValueError("Max delay must be positive")
        
        if not self.processes:
            raise ValueError("At least one process must be defined")
        
        for target in self.optimization_targets:
            if target != "time" and target not in self.initial_stocks:
                raise ValueError(f"Invalid optimization target: {target}")
        
        for stock_name, quantity in self.initial_stocks.items():
            if quantity < 0:
                raise ValueError(f"Stock '{stock_name}' has negative quantity: {quantity}")


@dataclass
class ProcessExecution:
    process_name: str
    start_cycle: int
    end_cycle: int
    resources_consumed: Dict[str, int]
    resources_produced: Dict[str, int]
    
    def __post_init__(self):
        if self.start_cycle < 0 or self.end_cycle < self.start_cycle:
            raise ValueError("Invalid cycle times")


@dataclass
class SimulationResult:
    executions: List[ProcessExecution]
    final_stocks: Dict[str, int]
    final_cycle: int
    termination_reason: str
    total_processes_executed: int = 0
    
    def __post_init__(self):
        self.total_processes_executed = len(self.executions)


@dataclass
class TraceEntry:
    cycle: int
    process_name: str
    
    def __post_init__(self):
        if self.cycle < 0:
            raise ValueError("Cycle must be non-negative")
        if not self.process_name.strip():
            raise ValueError("Process name cannot be empty")
    
    def __str__(self) -> str:
        return f"{self.cycle}:{self.process_name}"


@dataclass
class VerificationResult:
    is_valid: bool
    error_cycle: Optional[int] = None
    error_process: Optional[str] = None
    error_message: Optional[str] = None
    final_stocks: Optional[Dict[str, int]] = None
    final_cycle: int = 0
    
    def has_error(self) -> bool:
        return not self.is_valid
    
    def get_error_description(self) -> str:
        if self.is_valid:
            return "Verification successful"
        
        error_parts = []
        if self.error_cycle is not None:
            error_parts.append(f"Cycle {self.error_cycle}")
        if self.error_process:
            error_parts.append(f"Process '{self.error_process}'")
        if self.error_message:
            error_parts.append(self.error_message)
        
        return "Error: " + ", ".join(error_parts) if error_parts else "Unknown error"


class SimulationError(Exception):    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def get_detailed_message(self) -> str:
        if not self.details:
            return self.message
        
        detail_strs = [f"{k}: {v}" for k, v in self.details.items()]
        return f"{self.message}\nDetails: {', '.join(detail_strs)}"


class ConfigurationError(SimulationError):    
    def __init__(self, message: str, line_number: Optional[int] = None, file_path: Optional[str] = None):
        details = {}
        if line_number is not None:
            details['line'] = line_number
        if file_path is not None:
            details['file'] = file_path
        
        super().__init__(message, details)
        self.line_number = line_number
        self.file_path = file_path


class ResourceError(SimulationError):
    def __init__(self, message: str, cycle: Optional[int] = None,
                 process_name: Optional[str] = None,
                 resource_name: Optional[str] = None):
        details = {}
        if cycle is not None:
            details['cycle'] = cycle
        if process_name is not None:
            details['process'] = process_name
        if resource_name is not None:
            details['resource'] = resource_name
        
        super().__init__(message, details)
        self.cycle = cycle
        self.process_name = process_name
        self.resource_name = resource_name


class VerificationError(SimulationError):    
    def __init__(self, message: str, line_number: Optional[int] = None,
                 trace_file: Optional[str] = None):
        details = {}
        if line_number is not None:
            details['line'] = line_number
        if trace_file is not None:
            details['file'] = trace_file
        
        super().__init__(message, details)
        self.line_number = line_number
        self.trace_file = trace_file


class SchedulingError(SimulationError):    
    def __init__(self, message: str, cycle: Optional[int] = None,
                 process_name: Optional[str] = None):
        details = {}
        if cycle is not None:
            details['cycle'] = cycle
        if process_name is not None:
            details['process'] = process_name
        
        super().__init__(message, details)
        self.cycle = cycle
        self.process_name = process_name