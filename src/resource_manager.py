"""
Resource Management System for Process Simulation

This module provides the ResourceManager class for tracking and managing
resource stocks throughout the simulation lifecycle.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from src.data_models import ResourceError
from src.performance_monitor import CircularBuffer


@dataclass
class ResourceTransaction:
    """Record of a resource transaction"""
    cycle: int
    process_name: str
    resource_name: str
    quantity: int  # Positive for production, negative for consumption
    stock_after: int
    
    def __str__(self) -> str:
        action = "produced" if self.quantity > 0 else "consumed"
        return f"Cycle {self.cycle}: {self.process_name} {action} {abs(self.quantity)} {self.resource_name} (stock: {self.stock_after})"


class ResourceManager:
    """
    Manages resource stocks and transactions for the simulation.
    
    Responsibilities:
    - Track current stock levels for all resources
    - Check resource availability before process execution
    - Consume resources when processes execute
    - Produce resources when processes complete
    - Log all resource transactions for auditing
    """
    
    def __init__(self, initial_stocks: Dict[str, int], max_transaction_log: int = 100000):
        """
        Initialize the resource manager with initial stock levels.
        
        Args:
            initial_stocks: Dictionary mapping resource names to initial quantities
            max_transaction_log: Maximum number of transactions to keep in memory
            
        Raises:
            ValueError: If any initial stock quantity is negative
        """
        # Validate initial stocks
        for resource, quantity in initial_stocks.items():
            if quantity < 0:
                raise ValueError(f"Initial stock for '{resource}' cannot be negative: {quantity}")
        
        # Create a copy to avoid external modifications
        self._stocks: Dict[str, int] = initial_stocks.copy()
        self._transaction_log: List[ResourceTransaction] = []
        self._initial_stocks: Dict[str, int] = initial_stocks.copy()
        self._max_transaction_log = max_transaction_log
        self._use_circular_buffer = max_transaction_log > 0
    
    def get_stock(self, resource: str) -> int:
        """
        Get the current stock level for a resource.
        
        Args:
            resource: Name of the resource
            
        Returns:
            Current stock quantity (0 if resource doesn't exist)
        """
        return self._stocks.get(resource, 0)
    
    def get_all_stocks(self) -> Dict[str, int]:
        """
        Get a copy of all current stock levels.
        
        Returns:
            Dictionary mapping resource names to current quantities
        """
        return self._stocks.copy()
    
    def has_sufficient_resources(self, requirements: Dict[str, int]) -> bool:
        """
        Check if sufficient resources are available for the given requirements.
        
        Args:
            requirements: Dictionary mapping resource names to required quantities
            
        Returns:
            True if all required resources are available in sufficient quantities
        """
        for resource, required_qty in requirements.items():
            if required_qty < 0:
                return False  # Invalid requirement
            
            current_stock = self.get_stock(resource)
            if current_stock < required_qty:
                return False
        
        return True
    
    def consume_resources(self, 
                         process_name: str, 
                         resources: Dict[str, int], 
                         cycle: int) -> None:
        """
        Consume resources for a process execution.
        
        Args:
            process_name: Name of the process consuming resources
            resources: Dictionary mapping resource names to quantities to consume
            cycle: Current simulation cycle
            
        Raises:
            ResourceError: If insufficient resources are available
        """
        # Validate inputs
        if not process_name:
            raise ResourceError("Process name cannot be empty", cycle=cycle)
        
        if cycle < 0:
            raise ResourceError(
                f"Invalid cycle number: {cycle}",
                cycle=cycle,
                process_name=process_name
            )
        
        # Check for negative quantities first
        for resource, quantity in resources.items():
            if quantity < 0:
                raise ResourceError(
                    f"Cannot consume negative quantity of '{resource}': {quantity}",
                    cycle=cycle,
                    process_name=process_name,
                    resource_name=resource
                )
        
        # Then check if we have sufficient resources
        if not self.has_sufficient_resources(resources):
            missing = []
            for resource, required in resources.items():
                available = self.get_stock(resource)
                if available < required:
                    missing.append(f"{resource} (need {required}, have {available})")
            
            error_msg = f"Insufficient resources for process '{process_name}': {', '.join(missing)}"
            raise ResourceError(
                error_msg,
                cycle=cycle,
                process_name=process_name
            )
        
        # Consume the resources and log transactions
        for resource, quantity in resources.items():
            
            # Initialize resource if it doesn't exist
            if resource not in self._stocks:
                self._stocks[resource] = 0
            
            self._stocks[resource] -= quantity
            
            # Log the transaction
            transaction = ResourceTransaction(
                cycle=cycle,
                process_name=process_name,
                resource_name=resource,
                quantity=-quantity,  # Negative for consumption
                stock_after=self._stocks[resource]
            )
            self._transaction_log.append(transaction)
            
            # Prune transaction log if it gets too large
            if self._use_circular_buffer and len(self._transaction_log) > self._max_transaction_log:
                # Keep only the most recent transactions
                self._transaction_log = self._transaction_log[-self._max_transaction_log:]
    
    def produce_resources(self, 
                         process_name: str, 
                         resources: Dict[str, int], 
                         cycle: int) -> None:
        """
        Produce resources from a process completion.
        
        Args:
            process_name: Name of the process producing resources
            resources: Dictionary mapping resource names to quantities to produce
            cycle: Current simulation cycle
            
        Raises:
            ResourceError: If production quantities are invalid
        """
        # Validate inputs
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
            
            # Initialize resource if it doesn't exist
            if resource not in self._stocks:
                self._stocks[resource] = 0
            
            self._stocks[resource] += quantity
            
            # Log the transaction
            transaction = ResourceTransaction(
                cycle=cycle,
                process_name=process_name,
                resource_name=resource,
                quantity=quantity,  # Positive for production
                stock_after=self._stocks[resource]
            )
            self._transaction_log.append(transaction)
            
            # Prune transaction log if it gets too large
            if self._use_circular_buffer and len(self._transaction_log) > self._max_transaction_log:
                # Keep only the most recent transactions
                self._transaction_log = self._transaction_log[-self._max_transaction_log:]
    
    def get_transaction_log(self) -> List[ResourceTransaction]:
        """
        Get a copy of the complete transaction log.
        
        Returns:
            List of all resource transactions in chronological order
        """
        return self._transaction_log.copy()
    
    def get_transactions_for_cycle(self, cycle: int) -> List[ResourceTransaction]:
        """
        Get all transactions that occurred in a specific cycle.
        
        Args:
            cycle: The simulation cycle to query
            
        Returns:
            List of transactions from the specified cycle
        """
        return [t for t in self._transaction_log if t.cycle == cycle]
    
    def get_transactions_for_process(self, process_name: str) -> List[ResourceTransaction]:
        """
        Get all transactions for a specific process.
        
        Args:
            process_name: Name of the process
            
        Returns:
            List of transactions for the specified process
        """
        return [t for t in self._transaction_log if t.process_name == process_name]
    
    def reset(self) -> None:
        """
        Reset the resource manager to initial state.
        Clears transaction log and restores initial stock levels.
        """
        self._stocks = self._initial_stocks.copy()
        self._transaction_log.clear()
    
    def get_resource_names(self) -> List[str]:
        """
        Get a list of all known resource names.
        
        Returns:
            List of resource names
        """
        return list(self._stocks.keys())
    
    def __str__(self) -> str:
        """String representation of current stock levels"""
        stock_strs = [f"{name}:{qty}" for name, qty in sorted(self._stocks.items())]
        return f"ResourceManager({', '.join(stock_strs)})"
    
    def __repr__(self) -> str:
        return self.__str__()
