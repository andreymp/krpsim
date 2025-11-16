"""
Performance Monitoring and Optimization for Process Simulation

This module provides performance monitoring, memory-efficient data structures,
and configurable limits for large-scale simulations.
"""

import time
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque


@dataclass
class PerformanceMetrics:
    """Performance metrics for simulation execution"""
    start_time: float = 0.0
    end_time: float = 0.0
    total_cycles: int = 0
    total_executions: int = 0
    peak_memory_mb: float = 0.0
    avg_cycle_time_ms: float = 0.0
    
    def get_duration_seconds(self) -> float:
        """Get total execution duration in seconds"""
        return self.end_time - self.start_time if self.end_time > 0 else 0.0
    
    def get_executions_per_second(self) -> float:
        """Get average executions per second"""
        duration = self.get_duration_seconds()
        return self.total_executions / duration if duration > 0 else 0.0


@dataclass
class SimulationLimits:
    """Configurable limits and safeguards for simulations"""
    max_cycles: int = 100000
    max_executions: int = 1000000
    max_memory_mb: float = 1024.0
    max_execution_history: int = 100000
    enable_history_pruning: bool = True
    history_keep_recent: int = 10000
    
    def validate(self) -> None:
        """Validate that limits are reasonable"""
        if self.max_cycles <= 0:
            raise ValueError("max_cycles must be positive")
        if self.max_executions <= 0:
            raise ValueError("max_executions must be positive")
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.history_keep_recent > self.max_execution_history:
            raise ValueError("history_keep_recent cannot exceed max_execution_history")


class PerformanceMonitor:
    """
    Monitors and tracks performance metrics during simulation.
    
    Provides:
    - Execution time tracking
    - Memory usage monitoring
    - Cycle performance statistics
    - Configurable limits and safeguards
    """
    
    def __init__(self, limits: Optional[SimulationLimits] = None):
        """
        Initialize performance monitor.
        
        Args:
            limits: Optional simulation limits (uses defaults if not provided)
        """
        self._limits = limits or SimulationLimits()
        self._limits.validate()
        
        self._metrics = PerformanceMetrics()
        self._cycle_times: deque = deque(maxlen=1000)  # Keep last 1000 cycle times
        self._is_monitoring = False
        self._last_cycle_start = 0.0
    
    def start_monitoring(self) -> None:
        """Start performance monitoring"""
        self._metrics.start_time = time.time()
        self._is_monitoring = True
        self._last_cycle_start = time.time()
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring"""
        self._metrics.end_time = time.time()
        self._is_monitoring = False
        
        # Calculate average cycle time
        if self._cycle_times:
            avg_time_sec = sum(self._cycle_times) / len(self._cycle_times)
            self._metrics.avg_cycle_time_ms = avg_time_sec * 1000.0
    
    def record_cycle_start(self) -> None:
        """Record the start of a simulation cycle"""
        if self._is_monitoring:
            self._last_cycle_start = time.time()
    
    def record_cycle_end(self, cycle_number: int) -> None:
        """
        Record the end of a simulation cycle.
        
        Args:
            cycle_number: The cycle number that just completed
        """
        if self._is_monitoring:
            cycle_duration = time.time() - self._last_cycle_start
            self._cycle_times.append(cycle_duration)
            self._metrics.total_cycles = cycle_number
    
    def record_execution(self) -> None:
        """Record a process execution"""
        if self._is_monitoring:
            self._metrics.total_executions += 1
    
    def check_limits(self, current_cycle: int, execution_count: int) -> Optional[str]:
        """
        Check if any limits have been exceeded.
        
        Args:
            current_cycle: Current simulation cycle
            execution_count: Total number of executions so far
            
        Returns:
            Error message if limit exceeded, None otherwise
        """
        if current_cycle >= self._limits.max_cycles:
            return f"Maximum cycle limit exceeded: {self._limits.max_cycles}"
        
        if execution_count >= self._limits.max_executions:
            return f"Maximum execution limit exceeded: {self._limits.max_executions}"
        
        # Check memory usage
        memory_mb = self._get_memory_usage_mb()
        if memory_mb > self._limits.max_memory_mb:
            return f"Maximum memory limit exceeded: {memory_mb:.1f}MB > {self._limits.max_memory_mb}MB"
        
        return None
    
    def should_prune_history(self, history_size: int) -> bool:
        """
        Check if execution history should be pruned.
        
        Args:
            history_size: Current size of execution history
            
        Returns:
            True if history should be pruned
        """
        if not self._limits.enable_history_pruning:
            return False
        
        return history_size > self._limits.max_execution_history
    
    def get_history_prune_count(self, history_size: int) -> int:
        """
        Get number of history entries to remove during pruning.
        
        Args:
            history_size: Current size of execution history
            
        Returns:
            Number of entries to remove from the beginning
        """
        if history_size <= self._limits.history_keep_recent:
            return 0
        
        return history_size - self._limits.history_keep_recent
    
    def _get_memory_usage_mb(self) -> float:
        """
        Get current memory usage in MB.
        
        Returns:
            Memory usage in megabytes
        """
        try:
            import psutil
            process = psutil.Process()
            memory_bytes = process.memory_info().rss
            memory_mb = memory_bytes / (1024 * 1024)
            
            # Update peak memory
            if memory_mb > self._metrics.peak_memory_mb:
                self._metrics.peak_memory_mb = memory_mb
            
            return memory_mb
        except ImportError:
            # psutil not available, return 0
            return 0.0
    
    def get_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics.
        
        Returns:
            PerformanceMetrics object
        """
        return self._metrics
    
    def get_limits(self) -> SimulationLimits:
        """
        Get configured simulation limits.
        
        Returns:
            SimulationLimits object
        """
        return self._limits
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get performance summary as dictionary.
        
        Returns:
            Dictionary with performance statistics
        """
        metrics = self._metrics
        return {
            'duration_seconds': metrics.get_duration_seconds(),
            'total_cycles': metrics.total_cycles,
            'total_executions': metrics.total_executions,
            'executions_per_second': metrics.get_executions_per_second(),
            'avg_cycle_time_ms': metrics.avg_cycle_time_ms,
            'peak_memory_mb': metrics.peak_memory_mb,
        }
    
    def print_summary(self) -> None:
        """Print performance summary to console"""
        summary = self.get_summary()
        print("\n=== Performance Summary ===")
        print(f"Duration: {summary['duration_seconds']:.2f}s")
        print(f"Total Cycles: {summary['total_cycles']}")
        print(f"Total Executions: {summary['total_executions']}")
        print(f"Executions/Second: {summary['executions_per_second']:.1f}")
        print(f"Avg Cycle Time: {summary['avg_cycle_time_ms']:.3f}ms")
        if summary['peak_memory_mb'] > 0:
            print(f"Peak Memory: {summary['peak_memory_mb']:.1f}MB")
        print("=" * 27)


class CircularBuffer:
    """
    Memory-efficient circular buffer for storing execution history.
    
    Automatically overwrites oldest entries when capacity is reached.
    """
    
    def __init__(self, capacity: int):
        """
        Initialize circular buffer.
        
        Args:
            capacity: Maximum number of items to store
        """
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        
        self._capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)
    
    def append(self, item: Any) -> None:
        """
        Add item to buffer.
        
        Args:
            item: Item to add
        """
        self._buffer.append(item)
    
    def get_all(self) -> List[Any]:
        """
        Get all items in buffer.
        
        Returns:
            List of items in chronological order
        """
        return list(self._buffer)
    
    def get_recent(self, count: int) -> List[Any]:
        """
        Get most recent items.
        
        Args:
            count: Number of recent items to retrieve
            
        Returns:
            List of most recent items
        """
        if count >= len(self._buffer):
            return list(self._buffer)
        
        return list(self._buffer)[-count:]
    
    def size(self) -> int:
        """Get current number of items in buffer"""
        return len(self._buffer)
    
    def capacity(self) -> int:
        """Get maximum capacity of buffer"""
        return self._capacity
    
    def is_full(self) -> bool:
        """Check if buffer is at capacity"""
        return len(self._buffer) >= self._capacity
    
    def clear(self) -> None:
        """Clear all items from buffer"""
        self._buffer.clear()


def optimize_stock_dict(stocks: Dict[str, int]) -> Dict[str, int]:
    """
    Optimize stock dictionary by removing zero-value entries.
    
    Args:
        stocks: Stock dictionary to optimize
        
    Returns:
        Optimized dictionary with only non-zero stocks
    """
    return {k: v for k, v in stocks.items() if v != 0}


def estimate_memory_usage(obj: Any) -> int:
    """
    Estimate memory usage of an object in bytes.
    
    Args:
        obj: Object to estimate
        
    Returns:
        Estimated memory usage in bytes
    """
    return sys.getsizeof(obj)
