"""
Output Formatting System for Process Simulation

This module provides the OutputFormatter class for generating human-readable
and machine-readable output from simulation results.
"""

from typing import Dict, List, Optional, TextIO
import sys
from src.data_models import (
    SimulationResult, ProcessExecution, TraceEntry,
    VerificationResult
)


class OutputFormatter:
    """
    Handles all output formatting for simulation and verification.
    
    Responsibilities:
    - Format human-readable simulation progress display
    - Generate machine-readable trace files
    - Format final results with stock levels and statistics
    - Format verification results
    """
    
    def __init__(self, output_stream: Optional[TextIO] = None):
        """
        Initialize the output formatter.
        
        Args:
            output_stream: Stream to write output to (defaults to stdout)
        """
        self._output_stream = output_stream or sys.stdout
    
    def format_simulation_start(self, 
                                num_processes: int,
                                num_stocks: int,
                                num_targets: int) -> str:
        """
        Format simulation start message.
        
        Args:
            num_processes: Number of processes in configuration
            num_stocks: Number of stock items
            num_targets: Number of optimization targets
            
        Returns:
            Formatted start message
        """
        return (f"Nice file! {num_processes} processes, "
                f"{num_stocks} stocks, {num_targets} to optimize")
    
    def format_simulation_progress(self, cycle: int, process_name: str) -> str:
        """
        Format a single process execution for progress display.
        
        Args:
            cycle: Cycle number when process started
            process_name: Name of the process
            
        Returns:
            Formatted progress line
        """
        return f"{cycle}:{process_name}"

    def format_trace_entry(self, entry: TraceEntry) -> str:
        """
        Format a trace entry in machine-readable format.
        
        Args:
            entry: TraceEntry to format
            
        Returns:
            Formatted trace entry (cycle:process_name)
        """
        return str(entry)
    
    def format_final_stocks(self, stocks: Dict[str, int]) -> str:
        """
        Format final stock levels.
        
        Args:
            stocks: Dictionary of stock names to quantities
            
        Returns:
            Formatted stock display
        """
        lines = ["Stock :"]
        for name, qty in sorted(stocks.items()):
            lines.append(f"{name} => {qty}")
        return "\n".join(lines)
    
    def format_termination_message(self, cycle: int, reason: str) -> str:
        """
        Format simulation termination message.
        
        Args:
            cycle: Final cycle number
            reason: Reason for termination
            
        Returns:
            Formatted termination message
        """
        if reason == "max_cycles_reached":
            return f"Timeout :("
        elif reason == "no_more_processes":
            return f"no more process doable at time {cycle}"
        else:
            return f"Simulation ended at cycle {cycle}: {reason}"
    
    def format_simulation_result(self, result: SimulationResult) -> str:
        """
        Format complete simulation result for display.
        
        Args:
            result: SimulationResult to format
            
        Returns:
            Formatted result string
        """
        lines = ["Main walk", ""]
        
        # Format each execution
        for execution in result.executions:
            lines.append(self.format_simulation_progress(
                execution.start_cycle,
                execution.process_name
            ))
        
        # Add termination message
        lines.append("")
        lines.append(self.format_termination_message(
            result.final_cycle,
            result.termination_reason
        ))
        
        # Add stock information
        lines.append("")
        lines.append(self.format_final_stocks(result.final_stocks))
        
        return "\n".join(lines)

    def write_trace_file(self, 
                        result: SimulationResult,
                        output_file: str) -> None:
        """
        Write machine-readable trace file.
        
        Args:
            result: SimulationResult to write
            output_file: Path to output file
        """
        with open(output_file, 'w') as f:
            # Sort executions by cycle to ensure chronological order
            sorted_executions = sorted(result.executions, key=lambda e: e.start_cycle)
            
            # Write each execution as a trace entry
            for execution in sorted_executions:
                entry = TraceEntry(
                    cycle=execution.start_cycle,
                    process_name=execution.process_name
                )
                f.write(f"{self.format_trace_entry(entry)}\n")
            
            # Write final cycle number
            f.write(f"{result.final_cycle}\n")
    
    def display_simulation_result(self, result: SimulationResult) -> None:
        """
        Display simulation result to output stream.
        
        Args:
            result: SimulationResult to display
        """
        output = self.format_simulation_result(result)
        self._output_stream.write(output + "\n")
        self._output_stream.flush()
    
    def display_progress(self, cycle: int, process_name: str) -> None:
        """
        Display a single progress update.
        
        Args:
            cycle: Current cycle
            process_name: Process being executed
        """
        line = self.format_simulation_progress(cycle, process_name)
        self._output_stream.write(line + "\n")
        self._output_stream.flush()
    
    def display_message(self, message: str) -> None:
        """
        Display a general message.
        
        Args:
            message: Message to display
        """
        self._output_stream.write(message + "\n")
        self._output_stream.flush()
    
    def format_verification_result(self, result: VerificationResult) -> str:
        """
        Format verification result for display.
        
        Args:
            result: VerificationResult to format
            
        Returns:
            Formatted verification result
        """
        if result.is_valid:
            lines = ["Verification successful!"]
            lines.append(f"Final cycle: {result.final_cycle}")
            
            if result.final_stocks:
                lines.append("")
                lines.append(self.format_final_stocks(result.final_stocks))
            
            return "\n".join(lines)
        else:
            return result.get_error_description()

    def display_verification_result(self, result: VerificationResult) -> None:
        """
        Display verification result to output stream.
        
        Args:
            result: VerificationResult to display
        """
        output = self.format_verification_result(result)
        self._output_stream.write(output + "\n")
        self._output_stream.flush()
    
    def format_statistics(self, result: SimulationResult) -> str:
        """
        Format simulation statistics.
        
        Args:
            result: SimulationResult to analyze
            
        Returns:
            Formatted statistics string
        """
        lines = ["Simulation Statistics:"]
        lines.append(f"Total processes executed: {result.total_processes_executed}")
        lines.append(f"Final cycle: {result.final_cycle}")
        lines.append(f"Termination reason: {result.termination_reason}")
        
        # Count executions per process
        process_counts: Dict[str, int] = {}
        for execution in result.executions:
            process_counts[execution.process_name] = \
                process_counts.get(execution.process_name, 0) + 1
        
        if process_counts:
            lines.append("")
            lines.append("Executions per process:")
            for process_name, count in sorted(process_counts.items()):
                lines.append(f"  {process_name}: {count}")
        
        return "\n".join(lines)
    
    def display_statistics(self, result: SimulationResult) -> None:
        """
        Display simulation statistics to output stream.
        
        Args:
            result: SimulationResult to display statistics for
        """
        output = self.format_statistics(result)
        self._output_stream.write(output + "\n")
        self._output_stream.flush()
