import sys
import os
from typing import Optional

from verifier import TraceVerifier
from data_models import VerificationResult, VerificationError, ConfigurationError


def parse_arguments() -> tuple[str, str]:
    if len(sys.argv) != 3:
        print("Error: Wrong number of arguments", file=sys.stderr)
        print("Usage: python krpsim_verif.py <config_file.krpsim> <trace_file.txt>", file=sys.stderr)
        sys.exit(1)
    
    config_file = sys.argv[1]
    trace_file = sys.argv[2]
    
    if not config_file.endswith(".krpsim"):
        print("Error: Configuration file must have .krpsim extension", file=sys.stderr)
        sys.exit(1)
    
    if not trace_file.endswith(".txt"):
        print("Error: Trace file must have .txt extension", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found: {config_file}", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.exists(trace_file):
        print(f"Error: Trace file not found: {trace_file}", file=sys.stderr)
        sys.exit(1)
    
    return config_file, trace_file


def verify_trace(config_file: str, trace_file: str) -> VerificationResult:
    try:
        verifier = TraceVerifier(initial_stocks={}, processes=[])
        return verifier.verify_trace_file(config_file, trace_file)
        
    except Exception as e:
        return VerificationResult(
            is_valid=False,
            error_message=f"Unexpected error: {str(e)}"
        )


def display_verification_result(result: VerificationResult) -> None:
    if result.is_valid:
        print("Validation completed :)")
        
        if result.final_stocks:
            print("\nFinal stocks:")
            for resource, quantity in sorted(result.final_stocks.items()):
                print(f"  {resource}: {quantity}")
        
        if result.final_cycle > 0:
            print(f"\nSimulation completed at cycle: {result.final_cycle}")
    elif result.error_message:
        print(f"\n{result.get_error_description()}")

if __name__ == "__main__":
    config_file, trace_file = parse_arguments()    
    print("Parsing config file and validating result set...")
    
    result = verify_trace(config_file, trace_file)
    print("Evaluating .................. done.")
    display_verification_result(result)
