from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING, Any
from enum import Enum

if TYPE_CHECKING:
    from src.common import Process


class OptimizationTarget(Enum):
    """Enumeration of optimization target types"""
    TIME = "time"
    STOCK = "stock"


@dataclass
class SimulationConfig:
    """Configuration for a simulation run"""
    initial_stocks: Dict[str, int]
    processes: List['Process']
    optimization_targets: List[str]
    max_delay: int
    config_file: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        if self.max_delay <= 0:
            raise ValueError("Max delay must be positive")
        
        if not self.processes:
            raise ValueError("At least one process must be defined")
        
        # Validate optimization targets
        for target in self.optimization_targets:
            if target != "time" and target not in self.initial_stocks:
                raise ValueError(f"Invalid optimization target: {target}")
        
        # Validate initial stocks are non-negative
        for stock_name, quantity in self.initial_stocks.items():
            if quantity < 0:
                raise ValueError(f"Stock '{stock_name}' has negative quantity: {quantity}")


@dataclass
class ProcessExecution:
    """Record of a process execution"""
    process_name: str
    start_cycle: int
    end_cycle: int
    resources_consumed: Dict[str, int]
    resources_produced: Dict[str, int]
    
    def __post_init__(self):
        """Validate execution record"""
        if self.start_cycle < 0 or self.end_cycle < self.start_cycle:
            raise ValueError("Invalid cycle times")


@dataclass
class SimulationResult:
    """Complete result of a simulation run"""
    executions: List[ProcessExecution]
    final_stocks: Dict[str, int]
    final_cycle: int
    termination_reason: str
    total_processes_executed: int = 0
    
    def __post_init__(self):
        """Calculate derived statistics"""
        self.total_processes_executed = len(self.executions)


@dataclass
class TraceEntry:
    """Single entry in an execution trace"""
    cycle: int
    process_name: str
    
    def __post_init__(self):
        """Validate trace entry"""
        if self.cycle < 0:
            raise ValueError("Cycle must be non-negative")
        if not self.process_name.strip():
            raise ValueError("Process name cannot be empty")
    
    def __str__(self) -> str:
        """Format as required trace format: <cycle>:<process_name>"""
        return f"{self.cycle}:{self.process_name}"


@dataclass
class VerificationResult:
    """Result of trace verification"""
    is_valid: bool
    error_cycle: Optional[int] = None
    error_process: Optional[str] = None
    error_message: Optional[str] = None
    final_stocks: Optional[Dict[str, int]] = None
    final_cycle: int = 0
    
    def has_error(self) -> bool:
        """Check if verification found errors"""
        return not self.is_valid
    
    def get_error_description(self) -> str:
        """Get human-readable error description"""
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
    """Base exception for simulation errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize simulation error with message and optional details.
        
        Args:
            message: Error message
            details: Optional dictionary with additional error context
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def get_detailed_message(self) -> str:
        """Get error message with details"""
        if not self.details:
            return self.message
        
        detail_strs = [f"{k}: {v}" for k, v in self.details.items()]
        return f"{self.message}\nDetails: {', '.join(detail_strs)}"


class ConfigurationError(SimulationError):
    """Exception for configuration file errors"""
    
    def __init__(self, message: str, line_number: Optional[int] = None, 
                 file_path: Optional[str] = None):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            line_number: Line number where error occurred
            file_path: Path to configuration file
        """
        details = {}
        if line_number is not None:
            details['line'] = line_number
        if file_path is not None:
            details['file'] = file_path
        
        super().__init__(message, details)
        self.line_number = line_number
        self.file_path = file_path


class ResourceError(SimulationError):
    """Exception for resource management errors"""
    
    def __init__(self, message: str, cycle: Optional[int] = None,
                 process_name: Optional[str] = None,
                 resource_name: Optional[str] = None):
        """
        Initialize resource error.
        
        Args:
            message: Error message
            cycle: Cycle when error occurred
            process_name: Process that caused the error
            resource_name: Resource involved in the error
        """
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
    """Exception for trace verification errors"""
    
    def __init__(self, message: str, line_number: Optional[int] = None,
                 trace_file: Optional[str] = None):
        """
        Initialize verification error.
        
        Args:
            message: Error message
            line_number: Line number in trace file where error occurred
            trace_file: Path to trace file
        """
        details = {}
        if line_number is not None:
            details['line'] = line_number
        if trace_file is not None:
            details['file'] = trace_file
        
        super().__init__(message, details)
        self.line_number = line_number
        self.trace_file = trace_file


class SchedulingError(SimulationError):
    """Exception for scheduling errors"""
    
    def __init__(self, message: str, cycle: Optional[int] = None,
                 process_name: Optional[str] = None):
        """
        Initialize scheduling error.
        
        Args:
            message: Error message
            cycle: Cycle when error occurred
            process_name: Process that caused the error
        """
        details = {}
        if cycle is not None:
            details['cycle'] = cycle
        if process_name is not None:
            details['process'] = process_name
        
        super().__init__(message, details)
        self.cycle = cycle
        self.process_name = process_name