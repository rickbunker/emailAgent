"""
Memory monitoring utility for Email Agent.

Provides memory usage monitoring, automatic cleanup, and performance tracking
for all memory systems in the Email Agent application.

Phase 6.2 Implementation: Configuration & Memory Limits
"""

# # Standard library imports
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from .config import config
from .logging_system import get_logger, log_function

logger = get_logger(__name__)


@dataclass
class MemoryUsageStats:
    """Memory usage statistics for a single memory system."""

    collection_name: str
    current_items: int
    max_items: int
    usage_percentage: float
    estimated_size_mb: float
    last_cleanup: datetime | None
    cleanup_count: int
    performance_metrics: dict[str, float]


@dataclass
class SystemResourceStats:
    """System resource statistics."""

    memory_gb: float
    memory_used_percent: float
    disk_gb: float
    disk_used_percent: float
    cpu_usage_percent: float
    timestamp: datetime


class MemorySystem(Protocol):
    """Protocol for memory systems that can be monitored."""

    def get_collection_info(self) -> dict[str, Any]:
        """Get collection information including item count."""
        ...

    async def cleanup_old_items(self, batch_size: int) -> int:
        """Remove old items and return count of items removed."""
        ...


class MemoryMonitor:
    """
    Memory monitoring and management system.

    Provides automatic cleanup, usage tracking, and performance monitoring
    for all memory systems in the Email Agent application.
    """

    def __init__(self) -> None:
        """Initialize memory monitor with configuration."""
        self.is_running = False
        self.last_stats_log = datetime.now()
        self.memory_systems: dict[str, MemorySystem] = {}
        self.usage_history: list[SystemResourceStats] = []
        self.cleanup_history: dict[str, list[datetime]] = {}

    @log_function()
    def register_memory_system(self, name: str, memory_system: MemorySystem) -> None:
        """
        Register a memory system for monitoring.

        Args:
            name: Name of the memory system (e.g., 'semantic', 'episodic')
            memory_system: Memory system instance implementing MemorySystem protocol
        """
        self.memory_systems[name] = memory_system
        self.cleanup_history[name] = []
        logger.info(f"Registered memory system for monitoring: {name}")

    @log_function()
    def get_memory_usage_stats(self, name: str) -> MemoryUsageStats | None:
        """
        Get current memory usage statistics for a specific memory system.

        Args:
            name: Name of the memory system

        Returns:
            Memory usage statistics or None if system not found
        """
        if name not in self.memory_systems:
            logger.warning(f"Memory system not registered: {name}")
            return None

        try:
            memory_system = self.memory_systems[name]
            collection_info = memory_system.get_collection_info()

            current_items = collection_info.get("count", 0)
            max_items = getattr(config, f"{name}_memory_max_items", 10000)
            usage_percentage = (current_items / max_items) * 100 if max_items > 0 else 0

            # Estimate memory size (rough calculation: ~2KB per item)
            estimated_size_mb = (current_items * 2048) / (1024 * 1024)

            # Get last cleanup time
            last_cleanup = None
            if self.cleanup_history[name]:
                last_cleanup = max(self.cleanup_history[name])

            cleanup_count = len(self.cleanup_history[name])

            # Performance metrics (query time, etc.)
            performance_metrics = collection_info.get("performance_metrics", {})

            return MemoryUsageStats(
                collection_name=name,
                current_items=current_items,
                max_items=max_items,
                usage_percentage=usage_percentage,
                estimated_size_mb=estimated_size_mb,
                last_cleanup=last_cleanup,
                cleanup_count=cleanup_count,
                performance_metrics=performance_metrics,
            )

        except Exception as e:
            logger.error(f"Failed to get memory usage stats for {name}: {e}")
            return None

    @log_function()
    def get_all_memory_stats(self) -> dict[str, MemoryUsageStats]:
        """
        Get memory usage statistics for all registered memory systems.

        Returns:
            Dictionary mapping memory system names to their usage statistics
        """
        stats = {}
        for name in self.memory_systems:
            stat = self.get_memory_usage_stats(name)
            if stat:
                stats[name] = stat
        return stats

    @log_function()
    def get_system_resource_stats(self) -> SystemResourceStats:
        """
        Get current system resource statistics.

        Returns:
            Current system resource usage
        """
        resource_info = config.get_system_resource_info()

        return SystemResourceStats(
            memory_gb=resource_info["memory"]["available_gb"],
            memory_used_percent=resource_info["memory"]["used_percent"],
            disk_gb=resource_info["disk"]["available_gb"],
            disk_used_percent=resource_info["disk"]["used_percent"],
            cpu_usage_percent=resource_info["cpu"]["usage_percent"],
            timestamp=datetime.now(),
        )

    @log_function()
    async def check_and_cleanup_memory(self) -> dict[str, int]:
        """
        Check memory usage and perform cleanup if thresholds are exceeded.

        Returns:
            Dictionary mapping memory system names to number of items cleaned up
        """
        cleanup_results = {}

        for name, memory_system in self.memory_systems.items():
            try:
                stats = self.get_memory_usage_stats(name)
                if not stats:
                    continue

                # Check if cleanup is needed
                if stats.usage_percentage >= (config.memory_cleanup_threshold * 100):
                    logger.warning(
                        f"Memory cleanup triggered for {name}: {stats.usage_percentage:.1f}% "
                        f"(threshold: {config.memory_cleanup_threshold * 100:.1f}%)"
                    )

                    # Perform cleanup
                    items_removed = await memory_system.cleanup_old_items(
                        config.memory_cleanup_batch_size
                    )

                    cleanup_results[name] = items_removed
                    self.cleanup_history[name].append(datetime.now())

                    if items_removed > 0:
                        logger.info(
                            f"Cleaned up {items_removed} items from {name} memory system"
                        )
                    else:
                        logger.warning(
                            f"No items could be cleaned up from {name} memory system"
                        )

                elif stats.usage_percentage >= (config.memory_warning_threshold * 100):
                    logger.warning(
                        f"Memory warning for {name}: {stats.usage_percentage:.1f}% "
                        f"(warning threshold: {config.memory_warning_threshold * 100:.1f}%)"
                    )

            except Exception as e:
                logger.error(f"Failed to check/cleanup memory for {name}: {e}")

        return cleanup_results

    @log_function()
    def log_memory_statistics(self) -> None:
        """Log comprehensive memory and system statistics."""
        if not config.memory_performance_logging:
            return

        try:
            # Get all memory stats
            memory_stats = self.get_all_memory_stats()
            system_stats = self.get_system_resource_stats()

            logger.info("📊 Memory System Statistics:")

            total_items = 0
            total_size_mb = 0

            for name, stats in memory_stats.items():
                logger.info(
                    f"   {name.capitalize()}: {stats.current_items:,}/{stats.max_items:,} items "
                    f"({stats.usage_percentage:.1f}%) - {stats.estimated_size_mb:.1f}MB"
                )
                total_items += stats.current_items
                total_size_mb += stats.estimated_size_mb

                if stats.cleanup_count > 0:
                    logger.info(
                        f"      Cleanups: {stats.cleanup_count}, Last: {stats.last_cleanup}"
                    )

            logger.info(f"   Total: {total_items:,} items, {total_size_mb:.1f}MB")

            # System resources
            logger.info("🖥️  System Resources:")
            logger.info(
                f"   Memory: {system_stats.memory_gb:.1f}GB available "
                f"({100 - system_stats.memory_used_percent:.1f}% free)"
            )
            logger.info(
                f"   Disk: {system_stats.disk_gb:.1f}GB available "
                f"({100 - system_stats.disk_used_percent:.1f}% free)"
            )
            logger.info(f"   CPU: {system_stats.cpu_usage_percent:.1f}% usage")

            # Store system stats for trending
            self.usage_history.append(system_stats)

            # Keep only last 24 hours of history
            cutoff_time = datetime.now() - timedelta(hours=24)
            self.usage_history = [
                stat for stat in self.usage_history if stat.timestamp > cutoff_time
            ]

        except Exception as e:
            logger.error(f"Failed to log memory statistics: {e}")

    @log_function()
    async def start_monitoring(self) -> None:
        """Start the memory monitoring background task."""
        if self.is_running:
            logger.warning("Memory monitoring already running")
            return

        if not config.memory_monitoring_enabled:
            logger.info("Memory monitoring disabled in configuration")
            return

        self.is_running = True
        logger.info("Starting memory monitoring background task")

        try:
            while self.is_running:
                # Check and cleanup memory
                _ = await self.check_and_cleanup_memory()

                # Log statistics if interval has passed
                now = datetime.now()
                if (
                    now - self.last_stats_log
                ).total_seconds() >= config.memory_stats_log_interval:
                    self.log_memory_statistics()
                    self.last_stats_log = now

                # Wait for next check
                await asyncio.sleep(config.memory_usage_check_interval)

        except Exception as e:
            logger.error(f"Memory monitoring task failed: {e}")
        finally:
            self.is_running = False
            logger.info("Memory monitoring stopped")

    @log_function()
    def stop_monitoring(self) -> None:
        """Stop the memory monitoring background task."""
        if self.is_running:
            logger.info("Stopping memory monitoring")
            self.is_running = False
        else:
            logger.info("Memory monitoring not running")

    @log_function()
    def get_monitoring_status(self) -> dict[str, Any]:
        """
        Get current monitoring status and statistics.

        Returns:
            Dictionary with monitoring status and key metrics
        """
        memory_stats = self.get_all_memory_stats()
        system_stats = self.get_system_resource_stats()

        total_items = sum(stats.current_items for stats in memory_stats.values())
        total_max_items = sum(stats.max_items for stats in memory_stats.values())
        total_usage_percent = (
            (total_items / total_max_items * 100) if total_max_items > 0 else 0
        )

        return {
            "is_running": self.is_running,
            "registered_systems": list(self.memory_systems.keys()),
            "total_items": total_items,
            "total_max_items": total_max_items,
            "total_usage_percent": total_usage_percent,
            "system_memory_gb": system_stats.memory_gb,
            "system_memory_used_percent": system_stats.memory_used_percent,
            "system_disk_gb": system_stats.disk_gb,
            "system_disk_used_percent": system_stats.disk_used_percent,
            "cleanup_history_count": sum(
                len(history) for history in self.cleanup_history.values()
            ),
            "last_stats_log": self.last_stats_log.isoformat(),
            "memory_stats": {
                name: {
                    "current_items": stats.current_items,
                    "max_items": stats.max_items,
                    "usage_percentage": stats.usage_percentage,
                    "estimated_size_mb": stats.estimated_size_mb,
                    "cleanup_count": stats.cleanup_count,
                }
                for name, stats in memory_stats.items()
            },
        }


# Global memory monitor instance
memory_monitor = MemoryMonitor()
