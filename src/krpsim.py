import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Optional

from src.common import parse_config_to_simulation
from src.simulation_engine import SimulationEngine
from src.output_formatter import OutputFormatter
from src.data_models import SimulationConfig, ConfigurationError, SimulationError

RESULT_FILE = "result_set.txt"

def parse_arguments() -> tuple[str, int]:
    if len(sys.argv) != 3:
        print("Error: Wrong number of arguments")
        print("Usage: python krpsim.py <config_file.krpsim> <max_delay>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    delay_str = sys.argv[2]
    
    if not config_file.endswith(".krpsim"):
        print("Error: Configuration file must have .krpsim extension")
        sys.exit(1)
    
    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found: {config_file}")
        sys.exit(1)
    
    try:
        max_delay = int(delay_str)
        if max_delay <= 0:
            print("Error: Max delay must be a positive integer")
            sys.exit(1)
    except ValueError:
        print(f"Error: Invalid max delay value: '{delay_str}' (must be an integer)")
        sys.exit(1)
    
    return config_file, max_delay


def load_configuration(config_file: str, max_delay: int) -> Optional[SimulationConfig]:
    try:
        return parse_config_to_simulation(config_file, max_delay)
    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        return None
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error loading configuration: {e}")
        return None


def run_simulation(config: SimulationConfig, formatter: OutputFormatter) -> bool:
    try:
        start_msg = formatter.format_simulation_start(
            len(config.processes),
            len(config.initial_stocks),
            len(config.optimization_targets)
        )
        formatter.display_message(start_msg)
        
        engine = SimulationEngine(config)
        formatter.display_message("Evaluating .................. done.")
        
        result = engine.run()
        formatter.display_message("Main walk")
        formatter.display_message("")
        
        for execution in result.executions:
            formatter.display_progress(execution.start_cycle, execution.process_name)
        
        formatter.display_message("")
        termination_msg = formatter.format_termination_message(
            result.final_cycle,
            result.termination_reason
        )
        formatter.display_message(termination_msg)
        formatter.display_message("")
        formatter.display_message(formatter.format_final_stocks(result.final_stocks))
        
        # Create directory for result file if it has a directory component
        result_dir = os.path.dirname(RESULT_FILE)
        if result_dir:
            os.makedirs(result_dir, exist_ok=True)
        formatter.write_trace_file(result, RESULT_FILE)
        
        return True
        
    except SimulationError as e:
        print(f"Simulation Error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error during simulation: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    config_file, max_delay = parse_arguments()
    config = load_configuration(config_file, max_delay)
    if not config:
        sys.exit(1)
    
    run_simulation(config, OutputFormatter())
