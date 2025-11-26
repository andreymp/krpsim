from typing import Dict, List

from dataclasses import dataclass

from data_models import ResourceError

class ResourceManager:
    def __init__(self, initial_stocks: Dict[str, int]):
        for resource, quantity in initial_stocks.items():
            if quantity < 0:
                raise ValueError(f"Initial stock for '{resource}' cannot be negative: {quantity}")
        
        self._stocks: Dict[str, int] = initial_stocks.copy()
    
    def get_all_stocks(self) -> Dict[str, int]:
        return self._stocks.copy()
    
    def has_sufficient_resources(self, requirements: Dict[str, int]) -> bool:
        for resource, required_qty in requirements.items():
            if required_qty < 0:
                return False 
            
            current_stock = self._stocks.get(resource, 0)
            if current_stock < required_qty:
                return False
        return True
    
    def consume_resources(self, 
                         process_name: str, 
                         resources: Dict[str, int], 
                         cycle: int) -> None:
        if not process_name:
            raise ResourceError("Process name cannot be empty", cycle=cycle)
        
        if cycle < 0:
            raise ResourceError(
                f"Invalid cycle number: {cycle}",
                cycle=cycle,
                process_name=process_name
            )
        
        for resource, quantity in resources.items():
            if quantity < 0:
                raise ResourceError(
                    f"Cannot consume negative quantity of '{resource}': {quantity}",
                    cycle=cycle,
                    process_name=process_name,
                    resource_name=resource
                )
        
        if not self.has_sufficient_resources(resources):
            missing = []
            for resource, required in resources.items():
                available = self._stocks.get(resource, 0)
                if available < required:
                    missing.append(f"{resource} (need {required}, have {available})")
            raise ResourceError(
                f"Insufficient resources for process '{process_name}': {', '.join(missing)}",
                cycle=cycle,
                process_name=process_name
            )
    
        for resource, quantity in resources.items():
            if resource not in self._stocks:
                self._stocks[resource] = 0
            
            self._stocks[resource] -= quantity
    
    def produce_resources(self, 
                         process_name: str, 
                         resources: Dict[str, int], 
                         cycle: int) -> None:
        if not process_name:
            raise ResourceError("Process name cannot be empty", cycle=cycle)
        
        if cycle < 0:
            raise ResourceError(
                f"Invalid cycle number: {cycle}",
                cycle=cycle,
                process_name=process_name
            )
        
        for resource, quantity in resources.items():
            if quantity < 0:
                raise ResourceError(
                    f"Cannot produce negative quantity of '{resource}': {quantity}",
                    cycle=cycle,
                    process_name=process_name,
                    resource_name=resource
                )
            if resource not in self._stocks:
                self._stocks[resource] = 0
            
            self._stocks[resource] += quantity
