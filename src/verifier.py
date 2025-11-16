"""
Trace Verification System for Process Simulation

This module provides the TraceVerifier class for validating execution traces
against configuration files to ensure they represent valid simulation runs.
"""

import heapq
from typing import Dict, List, Tuple, Optional
from src.common import Process, parse_config
from src.data_models import (
    TraceEntry, VerificationResult, VerificationError,
    ConfigurationError
)


class TraceVerifier:
    """
    Verifies execution traces against simulation configurations.
    
    Responsibilities:
    - Parse trace files with format validation
    - Simulate trace execution to verify validity
    - Detect and report errors in traces
    - Track resource states during verification
    """
    
    def __init__(self, 
                 initial_stocks: Dict[str, int],
                 processes: List[Process]):
        """
        Initialize the trace verifier.
        
        Args:
            initial_stocks: Initial stock levels
            processes: List of available processes
        """
        self._initial_stocks = initial_stocks.copy()
        self._processes = {p.name: p for p in processes}
        self._current_stocks: Dict[str, int] = {}
        self._processes_in_progress: List[Tuple[int, int, Process]] = []
        self._current_cycle = 0
        self._process_counter = 0  # Counter for heap tie-breaking
    
    def parse_trace_file(self, trace_file: str) -> Tuple[List[TraceEntry], int]:
        """
        Parse a trace file and extract execution entries.
        
        Args:
            trace_file: Path to trace file
            
        Returns:
            Tuple of (list of TraceEntry objects, final cycle number)
            
        Raises:
            VerificationError: If trace file format is invalid
        """
        entries: List[TraceEntry] = []
        final_cycle: Optional[int] = None
        
        try:
            with open(trace_file, 'r') as f:
                lines = f.readlines()
                
            if not lines:
                raise VerificationError(
                    "Trace file is empty",
                    trace_file=trace_file
                )
            
            # Parse all lines
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Check if this is the final cycle line (last non-empty line)
                if ':' not in line:
                    # This should be the final cycle number
                    try:
                        final_cycle = int(line)
                        if final_cycle < 0:
                            raise VerificationError(
                                f"Final cycle must be non-negative, got {final_cycle}",
                                line_number=line_num,
                                trace_file=trace_file
                            )
                    except ValueError:
                        raise VerificationError(
                            f"Invalid final cycle format: '{line}'",
                            line_number=line_num,
                            trace_file=trace_file
                        )
                else:
                    # This is a trace entry
                    if ':' not in line:
                        raise VerificationError(
                            "Invalid trace entry format - missing ':'",
                            line_number=line_num,
                            trace_file=trace_file
                        )
                    
                    parts = line.split(':', 1)
                    if len(parts) != 2:
                        raise VerificationError(
                            f"Invalid trace entry format: '{line}'",
                            line_number=line_num,
                            trace_file=trace_file
                        )
                    
                    cycle_str, process_name = parts
                    
                    try:
                        cycle = int(cycle_str.strip())
                    except ValueError:
                        raise VerificationError(
                            f"Invalid cycle number: '{cycle_str}'",
                            line_number=line_num,
                            trace_file=trace_file
                        )
                    
                    process_name = process_name.strip()
                    if not process_name:
                        raise VerificationError(
                            "Empty process name",
                            line_number=line_num,
                            trace_file=trace_file
                        )
                    
                    # Create and validate trace entry
                    try:
                        entry = TraceEntry(cycle=cycle, process_name=process_name)
                        entries.append(entry)
                    except ValueError as e:
                        raise VerificationError(
                            str(e),
                            line_number=line_num,
                            trace_file=trace_file
                        )
            
            # Validate that we got a final cycle
            if final_cycle is None:
                raise VerificationError(
                    "Trace file missing final cycle number",
                    trace_file=trace_file
                )
            
            # Validate trace entries are in chronological order
            for i in range(1, len(entries)):
                if entries[i].cycle < entries[i-1].cycle:
                    raise VerificationError(
                        f"Trace entries not in chronological order: "
                        f"cycle {entries[i].cycle} comes after cycle {entries[i-1].cycle}",
                        trace_file=trace_file
                    )
            
            return entries, final_cycle
            
        except FileNotFoundError:
            raise VerificationError(
                f"Trace file not found: {trace_file}",
                trace_file=trace_file
            )
        except PermissionError:
            raise VerificationError(
                f"Permission denied reading trace file: {trace_file}",
                trace_file=trace_file
            )
        except VerificationError:
            raise
        except Exception as e:
            raise VerificationError(
                f"Error reading trace file: {str(e)}",
                trace_file=trace_file
            )
    
    def verify_trace(self, 
                     trace_entries: List[TraceEntry],
                     final_cycle: int) -> VerificationResult:
        """
        Verify that a trace represents a valid simulation execution.
        
        Args:
            trace_entries: List of trace entries to verify
            final_cycle: Expected final cycle number
            
        Returns:
            VerificationResult with validation outcome
        """
        # Reset state
        self._current_stocks = self._initial_stocks.copy()
        self._processes_in_progress = []
        self._current_cycle = 0
        
        try:
            # Process each trace entry
            for entry in trace_entries:
                # Advance time to the entry's cycle
                self._advance_to_cycle(entry.cycle)
                
                # Verify and execute the process
                error = self._execute_process_from_trace(entry)
                if error:
                    return error
            
            # Complete all remaining processes
            while self._processes_in_progress:
                self._current_cycle += 1
                self._complete_processes_at_cycle(self._current_cycle)
            
            # Verify final cycle matches
            if self._current_cycle != final_cycle:
                return VerificationResult(
                    is_valid=False,
                    error_cycle=self._current_cycle,
                    error_message=f"Final cycle mismatch: expected {final_cycle}, got {self._current_cycle}",
                    final_cycle=self._current_cycle
                )
            
            # Verification successful
            return VerificationResult(
                is_valid=True,
                final_stocks=self._current_stocks.copy(),
                final_cycle=final_cycle
            )
            
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                error_cycle=self._current_cycle,
                error_message=f"Unexpected error during verification: {str(e)}",
                final_cycle=self._current_cycle
            )
    
    def verify_trace_file(self, 
                         config_file: str,
                         trace_file: str) -> VerificationResult:
        """
        Verify a trace file against a configuration file.
        
        Args:
            config_file: Path to configuration file
            trace_file: Path to trace file
            
        Returns:
            VerificationResult with validation outcome
        """
        try:
            # Parse configuration
            stocks, processes, _ = parse_config(config_file)
            self._initial_stocks = stocks
            self._processes = {p.name: p for p in processes}
            
            # Parse trace file
            trace_entries, final_cycle = self.parse_trace_file(trace_file)
            
            # Verify trace
            return self.verify_trace(trace_entries, final_cycle)
            
        except VerificationError as e:
            return VerificationResult(
                is_valid=False,
                error_message=str(e)
            )
        except ConfigurationError as e:
            return VerificationResult(
                is_valid=False,
                error_message=f"Configuration error: {str(e)}"
            )
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _advance_to_cycle(self, target_cycle: int) -> None:
        """
        Advance simulation time to target cycle, completing processes along the way.
        
        Args:
            target_cycle: Cycle to advance to
        """
        while self._current_cycle < target_cycle:
            self._current_cycle += 1
            self._complete_processes_at_cycle(self._current_cycle)
    
    def _complete_processes_at_cycle(self, cycle: int) -> None:
        """
        Complete all processes that finish at the given cycle.
        
        Args:
            cycle: Current cycle number
        """
        while (self._processes_in_progress and 
               self._processes_in_progress[0][0] == cycle):
            _, _, process = heapq.heappop(self._processes_in_progress)
            
            # Add produced resources to stocks
            for resource, quantity in process.results.items():
                self._current_stocks[resource] = \
                    self._current_stocks.get(resource, 0) + quantity
    
    def _execute_process_from_trace(self, entry: TraceEntry) -> Optional[VerificationResult]:
        """
        Execute a process from a trace entry, validating it can be executed.
        
        Args:
            entry: TraceEntry to execute
            
        Returns:
            VerificationResult with error if execution fails, None if successful
        """
        # Check if process exists
        if entry.process_name not in self._processes:
            return VerificationResult(
                is_valid=False,
                error_cycle=entry.cycle,
                error_process=entry.process_name,
                error_message=f"Unknown process: '{entry.process_name}'",
                final_cycle=self._current_cycle
            )
        
        process = self._processes[entry.process_name]
        
        # Check if resources are available
        for resource, needed in process.needs.items():
            available = self._current_stocks.get(resource, 0)
            if available < needed:
                return VerificationResult(
                    is_valid=False,
                    error_cycle=entry.cycle,
                    error_process=entry.process_name,
                    error_message=(
                        f"Insufficient resources: need {needed} '{resource}', "
                        f"have {available}"
                    ),
                    final_cycle=self._current_cycle
                )
        
        # Consume resources
        for resource, needed in process.needs.items():
            self._current_stocks[resource] -= needed
        
        # Schedule process completion with counter for tie-breaking
        completion_cycle = entry.cycle + process.delay
        heapq.heappush(self._processes_in_progress, 
                      (completion_cycle, self._process_counter, process))
        self._process_counter += 1
        
        return None
    
    def get_current_stocks(self) -> Dict[str, int]:
        """
        Get current stock levels during verification.
        
        Returns:
            Dictionary of current stock levels
        """
        return self._current_stocks.copy()
    
    def get_current_cycle(self) -> int:
        """
        Get current cycle number during verification.
        
        Returns:
            Current cycle number
        """
        return self._current_cycle
