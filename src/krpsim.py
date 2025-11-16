#!/usr/bin/env python3
"""
krpsim - Process Simulation System

Main executable for running process simulations with resource management
and optimization.

Usage:
    python krpsim.py <config_file.krpsim> <max_delay>

Arguments:
    config_file: Path to configuration file (must end with .krpsim)
    max_delay: Maximum number of cycles to simulate
"""

import sys
import os
from typing import Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine
from src.output_formatter import OutputFormatter
from src.data_models import SimulationConfig, ConfigurationError, SimulationError


def parse_arguments() -> tuple[str, int]:
    """
    Parse and validate command-line arguments.
    
    Returns:
        Tuple of (config_file, max_delay)
        
    Raises:
        SystemExit: If arguments are invalid
    """
    if len(sys.argv) != 3:
        print("Error: Wrong number of arguments", file=sys.stderr)
        print("Usage: python krpsim.py <config_file.krpsim> <max_delay>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[1]
    delay_str = sys.argv[2]
    
    # Validate file extension
    if not config_file.endswith(".krpsim"):
        print("Error: Configuration file must have .krpsim extension", file=sys.stderr)
        sys.exit(1)
    
    # Validate file exists
    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found: {config_file}", file=sys.stderr)
        sys.exit(1)
    
    # Validate and parse delay
    try:
        max_delay = int(delay_str)
        if max_delay <= 0:
            print("Error: Max delay must be a positive integer", file=sys.stderr)
            sys.exit(1)
    except ValueError:
        print(f"Error: Invalid max delay value: '{delay_str}' (must be an integer)", file=sys.stderr)
        sys.exit(1)
    
    return config_file, max_delay


def load_configuration(config_file: str, max_delay: int) -> Optional[SimulationConfig]:
    """
    Load and parse configuration file.
    
    Args:
        config_file: Path to configuration file
        max_delay: Maximum delay for simulation
        
    Returns:
        SimulationConfig object or None if error
    """
    try:
        config = parse_config_to_simulation(config_file, max_delay)
        return config
    except ConfigurationError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return None
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error loading configuration: {e}", file=sys.stderr)
        return None


def run_simulation(config: SimulationConfig, formatter: OutputFormatter) -> bool:
    """
    Run the simulation and display results.
    
    Args:
        config: SimulationConfig object
        formatter: OutputFormatter for display
        
    Returns:
        True if simulation completed successfully, False otherwise
    """
    try:
        # Display start message
        start_msg = formatter.format_simulation_start(
            len(config.processes),
            len(config.initial_stocks),
            len(config.optimization_targets)
        )
        formatter.display_message(start_msg)
        
        # Create and run simulation engine
        engine = SimulationEngine(config)
        
        # Display progress message
        formatter.display_message("Evaluating .................. done.")
        
        # Run simulation
        result = engine.run()
        
        # Display results
        formatter.display_message("Main walk")
        formatter.display_message("")
        
        # Display each execution
        for execution in result.executions:
            formatter.display_progress(execution.start_cycle, execution.process_name)
        
        # Display termination message
        formatter.display_message("")
        termination_msg = formatter.format_termination_message(
            result.final_cycle,
            result.termination_reason
        )
        formatter.display_message(termination_msg)
        
        # Display final stocks
        formatter.display_message("")
        stock_display = formatter.format_final_stocks(result.final_stocks)
        formatter.display_message(stock_display)
        
        # Write trace file
        trace_file = "public/result_set.txt"
        os.makedirs(os.path.dirname(trace_file), exist_ok=True)
        formatter.write_trace_file(result, trace_file)
        
        return True
        
    except SimulationError as e:
        print(f"Simulation Error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error during simulation: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main() -> int:
    """
    Main entry point for krpsim.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse command-line arguments
    config_file, max_delay = parse_arguments()
    
    # Load configuration
    config = load_configuration(config_file, max_delay)
    if config is None:
        return 1
    
    # Create output formatter
    formatter = OutputFormatter()
    
    # Run simulation
    success = run_simulation(config, formatter)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
