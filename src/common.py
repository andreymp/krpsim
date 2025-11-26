import os

from typing import Dict, Tuple, List

from data_models import SimulationConfig, Process

def parse_config(config_file: str) -> Tuple[Dict[str, int], List[Process], List[str]]:
    stocks: Dict[str, int] = {}
    processes: List[Process] = []
    optimize_targets: List[str] = []

    def _make_stock_pair(prompt: str) -> Dict[str, int]:
        try:
            if not prompt.strip():
                raise ValueError("Empty stock")
            
            content = prompt.strip("()")
            if not content.strip():
                return {}
            
            pairs = {}
            for pair in content.split(";"):
                pair = pair.strip()
                if not pair:
                    continue
                    
                if ":" not in pair:
                    raise ValueError(f"Invalid stock format '{pair}' - missing ':'")
                
                parts = pair.split(":")
                if len(parts) != 2:
                    raise ValueError(f"Invalid stock format '{pair}' - too many ':'")
                
                name, qty_str = parts
                name = name.strip()
                if not name:
                    raise ValueError("Empty stock name")
                
                try:
                    qty = int(qty_str.strip())
                    if qty < 0:
                        raise ValueError(f"Negative quantity for '{name}': {qty}")
                    pairs[name] = qty
                except ValueError as e:
                    if "invalid literal" in str(e):
                        raise ValueError(f"Invalid quantity for '{name}': '{qty_str.strip()}'")
                    raise
            return pairs
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Error parsing stock specification: {str(e)}")
        
    def _get_delay(delay_str: str) -> int:
        try:
            delay = int(delay_str.strip())
            if delay <= 0:
                raise ValueError(f"Delay must be positive, got: {delay}")
            return delay
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(f"Invalid delay format: '{delay_str.strip()}'")
            raise
        except Exception as e:
            raise ValueError(f"Error parsing delay: {str(e)}")

    def _enrich_stocks(stocks_to_add: Dict[str, int], stocks: Dict[str, int]) -> Dict[str, int]:
        stocks_copy = stocks.copy()
        for name in stocks_to_add.keys():
            if name not in stocks_copy:
                stocks_copy[name] = 0
        return stocks_copy

    def _validate_file_exists(config_file: str):
        if not config_file:
            raise ValueError("Configuration file path cannot be empty")
        
        if not os.path.exists(config_file):
            raise ValueError(f"Configuration file not found: {config_file}")
        
        if not os.path.isfile(config_file):
            raise ValueError(f"Path is not a file: {config_file}")
        
        try:
            with open(config_file, 'r') as _:
                pass
        except PermissionError:
            raise ValueError(f"Permission denied reading file: {config_file}")
        except UnicodeDecodeError:
            raise ValueError(f"File is not a valid text file: {config_file}")
        except Exception as e:
            raise ValueError(f"Error accessing file {config_file}: {str(e)}")

    _validate_file_exists(config_file)
    
    try:
        with open(config_file, 'r') as f:
            optimize_nbr: int = 0

            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                try:
                    if line.startswith("optimize:"):
                        if optimize_nbr > 0:
                            raise ValueError("Multiple optimize lines not allowed")
                        
                        content = line[len("optimize:"):].strip()
                        if not content.startswith("(") or not content.endswith(")"):
                            raise ValueError("Malformed optimize line - must be optimize:(...)")
                        
                        optimize_nbr += 1
                        targets = content.strip("()").split(";")
                        optimize_targets.extend([t.strip() for t in targets if t.strip()])
                        
                        for target in optimize_targets:
                            if target != 'time' and target not in stocks:
                                raise ValueError(f"Invalid optimize target '{target}' - not in stocks")
                    elif ":" in line and "(" not in line:
                        if optimize_nbr > 0:
                            raise ValueError("Stock definitions must come before optimize directive")
                        
                        if line.count(":") != 1:
                            raise ValueError("Invalid stock format - expected 'name:quantity'")
                        
                        name, qty_str = line.split(":", 1)
                        name = name.strip()
                        if not name:
                            raise ValueError("Empty stock name")
                        
                        if name in stocks:
                            raise ValueError(f"Duplicate stock definition: '{name}'")
                        
                        try:
                            qty = int(qty_str.strip())
                            if qty < 0:
                                raise ValueError("Stock quantity must be non-negative: {qty}")
                            stocks[name] = qty
                        except ValueError as e:
                            if "invalid literal" in str(e):
                                raise ValueError(f"Invalid quantity for stock '{name}': '{qty_str.strip()}'")
                            raise
                    elif "(" in line:
                        if optimize_nbr > 0:
                            raise ValueError(f"Process definitions must come before optimize directive")
                        
                        colon_pos = line.find(":")
                        if colon_pos == -1:
                            raise ValueError("Missing ':' after process name")
                        
                        name = line[:colon_pos].strip()
                        if not name:
                            raise ValueError("Empty process name")
                        if any(p.name == name for p in processes):
                            raise ValueError(f"Duplicate process name: '{name}'")
                        
                        remainder = line[colon_pos + 1:]
                        
                        try:
                            parts = remainder.split("):(")
                            if len(parts) != 2:
                                raise ValueError("Invalid format")
                            
                            needs_part = parts[0]
                            if not needs_part.startswith("("):
                                needs_part = "(" + needs_part
                            needs = _make_stock_pair(needs_part)
                            stocks = _enrich_stocks(needs, stocks)
                            
                            results_delay_part = parts[1]
                            parts2 = results_delay_part.split("):")
                            if len(parts2) != 2:
                                raise ValueError("Invalid format")
                            
                            results_part = "(" + parts2[0] + ")"
                            delay_part = parts2[1]
                            results = _make_stock_pair(results_part)
                            delay = _get_delay(delay_part)
                            stocks = _enrich_stocks(results, stocks)
                            processes.append(Process(name, needs, results, delay))
                        except Exception as e:
                            raise ValueError(f"Invalid process format - expected 'name:(needs):(results):delay' - {str(e)}")
                    else:
                        raise ValueError(f"Wrong line format: '{line}'")
                except ValueError:
                    raise
                except Exception as e:
                    raise ValueError(f"Unexpected error: {str(e)}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error reading configuration file: {str(e)}")
    
    if not processes:
        raise ValueError("No processes defined in configuration file")
    
    return stocks, processes, optimize_targets


def parse_config_to_simulation(config_file: str, max_delay: int):
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
