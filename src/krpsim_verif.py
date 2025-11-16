#!/usr/bin/env python3
"""
krpsim_verif - Process Simulation Trace Verifier

Main executable for verifying execution traces against configuration files
to ensure they represent valid simulation runs.

Usage:
    python krpsim_verif.py <config_file.krpsim> <trace_file.txt>

Arguments:
    config_file: Path to configuration file (must end with .krpsim)
    trace_file: Path to trace file (must end with .txt)
"""

import sys
import os
from typing import Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.verifier import TraceVerifier
from src.data_models import VerificationResult, VerificationError, ConfigurationError


def parse_arguments() -> tuple[str, str]:
    """
    Parse and validate command-line arguments.
    
    Returns:
        Tuple of (config_file, trace_file)
        
    Raises:
        SystemExit: If arguments are invalid
    """
    if len(sys.argv) != 3:
        print("Error: Wrong number of arguments", file=sys.stderr)
        print("Usage: python krpsim_verif.py <config_file.krpsim> <trace_file.txt>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[1]
    trace_file = sys.argv[2]
    
    # Validate config file extension
    if not config_file.endswith(".krpsim"):
        print("Error: Configuration file must have .krpsim extension", file=sys.stderr)
        sys.exit(1)
    
    # Validate trace file extension
    if not trace_file.endswith(".txt"):
        print("Error: Trace file must have .txt extension", file=sys.stderr)
        sys.exit(1)
    
    # Validate config file exists
    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found: {config_file}", file=sys.stderr)
        sys.exit(1)
    
    # Validate trace file exists
    if not os.path.exists(trace_file):
        print(f"Error: Trace file not found: {trace_file}", file=sys.stderr)
        sys.exit(1)
    
    return config_file, trace_file


def verify_trace(config_file: str, trace_file: str) -> VerificationResult:
    """
    Verify a trace file against a configuration file.
    
    Args:
        config_file: Path to configuration file
        trace_file: Path to trace file
        
    Returns:
        VerificationResult object with validation outcome
    """
    try:
        # Create verifier (it will load config internally)
        verifier = TraceVerifier(initial_stocks={}, processes=[])
        
        # Verify trace file
        result = verifier.verify_trace_file(config_file, trace_file)
        
        return result
        
    except Exception as e:
        # Catch any unexpected errors
        return VerificationResult(
            is_valid=False,
            error_message=f"Unexpected error: {str(e)}"
        )


def display_verification_result(result: VerificationResult) -> None:
    """
    Display verification result to user.
    
    Args:
        result: VerificationResult to display
    """
    if result.is_valid:
        print("Validation completed :)")
        
        # Display final stocks if available
        if result.final_stocks:
            print("\nFinal stocks:")
            for resource, quantity in sorted(result.final_stocks.items()):
                print(f"  {resource}: {quantity}")
        
        # Display final cycle
        if result.final_cycle > 0:
            print(f"\nSimulation completed at cycle: {result.final_cycle}")
    else:
        print("Validation failed :(")
        
        # Display error details
        if result.error_message:
            print(f"\n{result.get_error_description()}")


def main() -> int:
    """
    Main entry point for krpsim_verif.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Parse command-line arguments
    config_file, trace_file = parse_arguments()
    
    # Display start message
    print("Parsing config file and validating result set...")
    
    # Verify trace
    result = verify_trace(config_file, trace_file)
    
    # Display evaluation message
    print("Evaluating .................. done.")
    
    # Display results
    display_verification_result(result)
    
    # Return exit code based on validation result
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
