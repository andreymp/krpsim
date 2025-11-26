import heapq

from typing import Dict, List, Tuple, Optional

from .common import Process, parse_config
from .data_models import (
    TraceEntry, VerificationResult, VerificationError,
    ConfigurationError
)


class TraceVerifier:
    def __init__(self, 
                 initial_stocks: Dict[str, int],
                 processes: List[Process]):
        self._initial_stocks = initial_stocks.copy()
        self._processes = {p.name: p for p in processes}
        self._current_stocks: Dict[str, int] = {}
        self._processes_in_progress: List[Tuple[int, int, Process]] = []
        self._current_cycle = 0
        self._process_counter = 0 
    
    def parse_trace_file(self, trace_file: str) -> Tuple[List[TraceEntry], int]:
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
                    try:
                        entry = TraceEntry(cycle=cycle, process_name=process_name)
                        entries.append(entry)
                    except ValueError as e:
                        raise VerificationError(
                            str(e),
                            line_number=line_num,
                            trace_file=trace_file
                        )
            
            if final_cycle is None:
                raise VerificationError(
                    "Trace file missing final cycle number",
                    trace_file=trace_file
                )
            
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
        self._current_stocks = self._initial_stocks.copy()
        self._processes_in_progress = []
        self._current_cycle = 0
        
        try:
            for entry in trace_entries:
                self._advance_to_cycle(entry.cycle)

                error = self._execute_process_from_trace(entry)
                if error:
                    return error
            
            while self._processes_in_progress:
                self._current_cycle += 1
                self._complete_processes_at_cycle(self._current_cycle)
            
            if self._current_cycle != final_cycle:
                return VerificationResult(
                    is_valid=False,
                    error_cycle=self._current_cycle,
                    error_message=f"Final cycle mismatch: expected {final_cycle}, got {self._current_cycle}",
                    final_cycle=self._current_cycle
                )
            
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
        try:
            stocks, processes, _ = parse_config(config_file)
            self._initial_stocks = stocks
            self._processes = {p.name: p for p in processes}
            trace_entries, final_cycle = self.parse_trace_file(trace_file)
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
        while self._current_cycle < target_cycle:
            self._current_cycle += 1
            self._complete_processes_at_cycle(self._current_cycle)
    
    def _complete_processes_at_cycle(self, cycle: int) -> None:
        while (self._processes_in_progress and 
               self._processes_in_progress[0][0] == cycle):
            _, _, process = heapq.heappop(self._processes_in_progress)
            
            # Add produced resources to stocks
            for resource, quantity in process.results.items():
                self._current_stocks[resource] = \
                    self._current_stocks.get(resource, 0) + quantity
    
    def _execute_process_from_trace(self, entry: TraceEntry) -> Optional[VerificationResult]:
        if entry.process_name not in self._processes:
            return VerificationResult(
                is_valid=False,
                error_cycle=entry.cycle,
                error_process=entry.process_name,
                error_message=f"Unknown process: '{entry.process_name}'",
                final_cycle=self._current_cycle
            )
        
        process = self._processes[entry.process_name]
        
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
        
        for resource, needed in process.needs.items():
            self._current_stocks[resource] -= needed
        
        completion_cycle = entry.cycle + process.delay
        heapq.heappush(self._processes_in_progress, 
                      (completion_cycle, self._process_counter, process))
        self._process_counter += 1
        
        return None
    
    def get_current_stocks(self) -> Dict[str, int]:
        return self._current_stocks.copy()
    
    def get_current_cycle(self) -> int:
        return self._current_cycle
