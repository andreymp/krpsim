import sys

from typing import Dict, Optional, TextIO

from data_models import SimulationResult, TraceEntry, VerificationResult


class OutputFormatter:
    def __init__(self, output_stream: Optional[TextIO] = None):
        self._output_stream = output_stream or sys.stdout
    
    def format_simulation_start(self, 
                                num_processes: int,
                                num_stocks: int,
                                num_targets: int) -> str:
        return (f"Nice file! {num_processes} processes, "
                f"{num_stocks} stocks, {num_targets} to optimize")
    
    def format_final_stocks(self, stocks: Dict[str, int]) -> str:
        lines = ["Stock :"]
        for name, qty in sorted(stocks.items()):
            lines.append(f"{name} => {qty}")
        return "\n".join(lines)
    
    def format_termination_message(self, cycle: int, reason: str) -> str:
        if reason == "max_cycles_reached":
            return f"Timeout :("
        elif reason == "no_more_processes":
            return f"no more process doable at time {cycle}"
        else:
            return f"Simulation ended at cycle {cycle}: {reason}"

    def write_trace_file(self, 
                        result: SimulationResult,
                        output_file: str) -> None:
        with open(output_file, 'w') as f:
            sorted_executions = sorted(result.executions, key=lambda e: e.start_cycle)
            for execution in sorted_executions:
                entry = TraceEntry(
                    cycle=execution.start_cycle,
                    process_name=execution.process_name
                )
                f.write(f"{self._format_trace_entry(entry)}\n")

            f.write(f"{result.final_cycle}\n")
    
    def display_progress(self, cycle: int, process_name: str) -> None:
        line = self._format_simulation_progress(cycle, process_name)
        self._output_stream.write(line + "\n")
        self._output_stream.flush()
    
    def display_message(self, message: str) -> None:
        self._output_stream.write(message + "\n")
        self._output_stream.flush()

    def display_verification_result(self, result: VerificationResult) -> None:
        output = self._format_verification_result(result)
        self._output_stream.write(output + "\n")
        self._output_stream.flush()
    
    def _format_simulation_progress(self, cycle: int, process_name: str) -> str:
        return f"{cycle}:{process_name}"

    def _format_trace_entry(self, entry: TraceEntry) -> str:
        return str(entry)

    def _format_verification_result(self, result: VerificationResult) -> str:
        if result.is_valid:
            lines = ["Verification successful!"]
            lines.append(f"Final cycle: {result.final_cycle}")
            
            if result.final_stocks:
                lines.append("")
                lines.append(self.format_final_stocks(result.final_stocks))
            
            return "\n".join(lines)
        else:
            return result.get_error_description()
