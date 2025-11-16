import sys
import heapq
from typing import Dict, Tuple, List, Optional, Union

class Process:
    def __init__(self, name: str, needs: Dict[str, int], results: Dict[str, int], delay: int):
        self.name: str = name
        self.needs: Dict[str, int] = needs
        self.results: Dict[str, int] = results
        self.delay: int = delay
        self.start_times: List[int] = []
        self.priority_score: float = 0.0
        self.execution_count: int = 0
        self.last_execution_cycle: int = -1
    
    def can_execute(self, available_stocks: Dict[str, int]) -> bool:
        """Check if process can execute with available stocks"""
        for resource, needed in self.needs.items():
            if available_stocks.get(resource, 0) < needed:
                return False
        return True
    
    def calculate_resource_efficiency(self) -> float:
        """Calculate efficiency as output value per input cost"""
        if not self.needs:
            return float('inf')  # No cost processes are highly efficient
        
        input_cost = sum(self.needs.values())
        output_value = sum(self.results.values())
        return output_value / input_cost if input_cost > 0 else 0.0
    
    def get_completion_cycle(self, start_cycle: int) -> int:
        """Get the cycle when this process will complete"""
        return start_cycle + self.delay
    
    def calculate_priority_score(self, 
                                 current_stocks: Dict[str, int], 
                                 optimization_targets: List[str],
                                 current_cycle: int) -> float:
        """
        Calculate priority score for process selection
        Higher score = higher priority
        
        Factors considered:
        - Resource efficiency (output/input ratio)
        - Alignment with optimization targets
        - Delay (prefer faster processes)
        - Stock scarcity (prefer processes that produce scarce resources)
        """
        score = 0.0
        
        # Base efficiency score
        efficiency = self.calculate_resource_efficiency()
        if efficiency != float('inf'):
            score += efficiency * 10.0
        else:
            score += 100.0  # High bonus for no-cost processes
        
        # Optimization target alignment
        for target in optimization_targets:
            if target == "time":
                # Prefer faster processes for time optimization
                score += 100.0 / (self.delay + 1)
            elif target in self.results:
                # Prefer processes that produce optimization targets
                score += self.results[target] * 50.0
        
        # Stock scarcity bonus - prefer producing scarce resources
        for resource, quantity in self.results.items():
            current_stock = current_stocks.get(resource, 0)
            if current_stock < 10:  # Arbitrary threshold for "scarce"
                score += (10 - current_stock) * quantity * 2.0
        
        # Delay penalty - prefer faster processes
        score -= self.delay * 0.5
        
        # Execution frequency penalty - avoid over-executing same process
        if self.execution_count > 0:
            score -= self.execution_count * 0.1
        
        self.priority_score = score
        return score
    
    def record_execution(self, start_cycle: int) -> None:
        """Record that this process was executed at the given cycle"""
        self.start_times.append(start_cycle)
        self.execution_count += 1
        self.last_execution_cycle = start_cycle
    
    def get_execution_history(self) -> List[int]:
        """Get list of all start cycles when this process was executed"""
        return self.start_times.copy()
    
    def reset_execution_tracking(self) -> None:
        """Reset execution tracking (useful for new simulations)"""
        self.start_times = []
        self.execution_count = 0
        self.last_execution_cycle = -1
        self.priority_score = 0.0
    
    def __str__(self) -> str:
        return f"Process({self.name}, delay={self.delay}, executions={self.execution_count})"
    
    def __repr__(self) -> str:
        return self.__str__()

def parse_config(config_file: str) -> Tuple[Dict[str, int], List[Process], List[str]]:
    """
    Enhanced parser with better error handling and validation
    Returns: (stocks, processes, optimization_targets)
    """
    stocks: Dict[str, int] = {}
    processes: List[Process] = []
    optimize_targets: List[str] = []

    def _make_stock_pair(prompt: str, line_num: int) -> Dict[str, int]:
        """Parse stock pairs with detailed error reporting"""
        try:
            if not prompt.strip():
                raise ValueError(f"Line {line_num}: Empty stock specification")
            
            # Handle empty parentheses () - valid for processes with no needs/results
            content = prompt.strip("()")
            if not content.strip():
                return {}  # Empty dict for no resources
            
            pairs = {}
            for pair in content.split(";"):
                pair = pair.strip()
                if not pair:  # Skip empty pairs from trailing semicolons
                    continue
                    
                if ":" not in pair:
                    raise ValueError(f"Line {line_num}: Invalid stock format '{pair}' - missing ':'")
                
                parts = pair.split(":")
                if len(parts) != 2:
                    raise ValueError(f"Line {line_num}: Invalid stock format '{pair}' - too many ':'")
                
                name, qty_str = parts
                name = name.strip()
                if not name:
                    raise ValueError(f"Line {line_num}: Empty stock name")
                
                try:
                    qty = int(qty_str.strip())
                    if qty < 0:
                        raise ValueError(f"Line {line_num}: Negative quantity for '{name}': {qty}")
                    pairs[name] = qty
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Line {line_num}: Invalid quantity for '{name}': '{qty_str.strip()}'")
                    raise
            
            return pairs
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Line {line_num}: Error parsing stock specification: {str(e)}")
        
    def _get_delay(prompt: str, line_num: int) -> int:
        """Parse delay with error reporting"""
        try:
            delay = int(prompt.strip())
            if delay <= 0:
                raise ValueError(f"Line {line_num}: Delay must be positive, got: {delay}")
            return delay
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(f"Line {line_num}: Invalid delay format: '{prompt.strip()}'")
            raise
        except Exception as e:
            raise ValueError(f"Line {line_num}: Error parsing delay: {str(e)}")

    def _enrich_stocks(stocks_to_add: Dict[str, int], stocks: Dict[str, int]) -> Dict[str, int]:
        """Add new stock types to the stocks dictionary"""
        stocks_copy = stocks.copy()
        for name in stocks_to_add.keys():
            if name not in stocks_copy:
                stocks_copy[name] = 0  # Initialize new stock types with 0
        return stocks_copy

    def _validate_file_exists(config_file: str):
        """Validate that the configuration file exists"""
        import os
        
        if not config_file:
            raise ValueError("Configuration file path cannot be empty")
        
        if not os.path.exists(config_file):
            raise ValueError(f"Configuration file not found: {config_file}")
        
        if not os.path.isfile(config_file):
            raise ValueError(f"Path is not a file: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                pass
        except PermissionError:
            raise ValueError(f"Permission denied reading file: {config_file}")
        except UnicodeDecodeError:
            raise ValueError(f"File is not a valid text file: {config_file}")
        except Exception as e:
            raise ValueError(f"Error accessing file {config_file}: {str(e)}")

    # Validate file exists
    _validate_file_exists(config_file)
    
    try:
        with open(config_file, 'r') as f:
            optimize_nbr: int = 0
            line_num = 0
            
            for line in f:
                line_num += 1
                original_line = line
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                try:
                    # Parse optimization directive
                    if line.startswith("optimize:"):
                        if optimize_nbr > 0:
                            raise ValueError(f"Line {line_num}: Multiple optimize directives not allowed")
                        
                        content = line[len("optimize:"):].strip()
                        if not content.startswith("(") or not content.endswith(")"):
                            raise ValueError(f"Line {line_num}: Malformed optimize line - must be optimize:(...)")
                        
                        optimize_nbr += 1
                        targets = content.strip("()").split(";")
                        optimize_targets.extend([t.strip() for t in targets if t.strip()])
                        
                        # Validate optimization targets
                        for target in optimize_targets:
                            if target != 'time' and target not in stocks:
                                raise ValueError(f"Line {line_num}: Invalid optimize target '{target}' - not in stocks")
                    
                    # Parse stock definition
                    elif ":" in line and "(" not in line:
                        if optimize_nbr > 0:
                            raise ValueError(f"Line {line_num}: Stock definitions must come before optimize directive")
                        
                        if line.count(":") != 1:
                            raise ValueError(f"Line {line_num}: Invalid stock format - expected 'name:quantity'")
                        
                        name, qty_str = line.split(":", 1)
                        name = name.strip()
                        
                        if not name:
                            raise ValueError(f"Line {line_num}: Empty stock name")
                        
                        if name in stocks:
                            raise ValueError(f"Line {line_num}: Duplicate stock definition: '{name}'")
                        
                        try:
                            qty = int(qty_str.strip())
                            if qty < 0:
                                raise ValueError(f"Line {line_num}: Stock quantity must be non-negative: {qty}")
                            stocks[name] = qty
                        except ValueError as e:
                            if "invalid literal" in str(e):
                                raise ValueError(f"Line {line_num}: Invalid quantity for stock '{name}': '{qty_str.strip()}'")
                            raise
                    
                    # Parse process definition
                    elif "(" in line:
                        if optimize_nbr > 0:
                            raise ValueError(f"Line {line_num}: Process definitions must come before optimize directive")
                        
                        # Split process definition - find the first colon for the name
                        colon_pos = line.find(":")
                        if colon_pos == -1:
                            raise ValueError(f"Line {line_num}: Missing ':' after process name")
                        
                        name = line[:colon_pos].strip()
                        if not name:
                            raise ValueError(f"Line {line_num}: Empty process name")
                        
                        # Check for duplicate process names
                        if any(p.name == name for p in processes):
                            raise ValueError(f"Line {line_num}: Duplicate process name: '{name}'")
                        
                        remainder = line[colon_pos + 1:]
                        
                        # Use the original parsing logic but with better error handling
                        try:
                            parts = remainder.split("):(")
                            if len(parts) != 2:
                                raise ValueError("Invalid format")
                            
                            # Parse needs
                            needs_part = parts[0]
                            if not needs_part.startswith("("):
                                needs_part = "(" + needs_part
                            needs = _make_stock_pair(needs_part, line_num)
                            
                            # Parse results and delay
                            results_delay_part = parts[1]
                            parts2 = results_delay_part.split("):")
                            if len(parts2) != 2:
                                raise ValueError("Invalid format")
                            
                            results_part = "(" + parts2[0] + ")"
                            delay_part = parts2[1]
                            
                            results = _make_stock_pair(results_part, line_num)
                            delay = _get_delay(delay_part, line_num)
                            
                            # Enrich stocks with new resource types
                            stocks = _enrich_stocks(needs, stocks)
                            stocks = _enrich_stocks(results, stocks)
                            
                            # Create process
                            processes.append(Process(name, needs, results, delay))
                            
                        except Exception as e:
                            raise ValueError(f"Line {line_num}: Invalid process format - expected 'name:(needs):(results):delay' - {str(e)}")
                    
                    else:
                        raise ValueError(f"Line {line_num}: Unrecognized line format: '{line}'")
                
                except ValueError:
                    raise
                except Exception as e:
                    raise ValueError(f"Line {line_num}: Unexpected error: {str(e)}")
    
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error reading configuration file: {str(e)}")
    
    # Final validation
    if not processes:
        raise ValueError("No processes defined in configuration file")
    
    return stocks, processes, optimize_targets


def parse_config_to_simulation(config_file: str, max_delay: int = 10000):
    """
    Parse configuration file and return a SimulationConfig object
    
    Args:
        config_file: Path to configuration file
        max_delay: Maximum delay for simulation (default: 10000)
    
    Returns:
        SimulationConfig object with parsed configuration
    
    Raises:
        ValueError: If configuration is invalid
    """
    # Import here to avoid circular dependency
    from src.data_models import SimulationConfig
    
    try:
        stocks, processes, optimize_targets = parse_config(config_file)
        
        return SimulationConfig(
            initial_stocks=stocks,
            processes=processes,
            optimization_targets=optimize_targets,
            max_delay=max_delay,
            config_file=config_file
        )
    except ValueError as e:
        raise ValueError(f"Failed to parse configuration: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error parsing configuration: {str(e)}")
