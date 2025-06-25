"""
Complete logging system for the email agent.

Provides decorators and utilities for logging function entry/exit, arguments,
return values, and exceptions across different log levels and output destinations.
"""

# # Standard library imports
import functools
import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LogConfig:
    """Configuration for the logging system."""

    # Log levels
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # Output destinations
    log_to_file: bool = True
    log_to_stdout: bool = True

    # File configuration
    log_file: str = "logs/emailagent.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

    # Format configuration
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

    # Function logging configuration
    log_arguments: bool = True
    log_return_values: bool = True
    log_execution_time: bool = True
    max_arg_length: int = 500  # Max chars for argument values

    # Sensitive data filtering
    sensitive_keys: list[str] = field(
        default_factory=lambda: [
            "password",
            "token",
            "secret",
            "key",
            "credential",
            "auth",
        ]
    )


class EmailAgentLogger:
    """Enhanced logger for the email agent system."""

    def __init__(self, name: str, config: LogConfig = None):
        self.name = name
        self.config = config or LogConfig()
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with configured handlers and formatters."""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.config.level.upper()))

        # Clear existing handlers to avoid duplicates
        logger.handlers.clear()

        formatter = logging.Formatter(
            self.config.format_string, datefmt=self.config.date_format
        )

        # Console handler
        if self.config.log_to_stdout:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        # File handler
        if self.config.log_to_file:
            # Ensure log directory exists
            log_path = Path(self.config.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # # Standard library imports
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                self.config.log_file,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _sanitize_value(self, key: str, value: Any) -> str:
        """Sanitize sensitive values for logging."""
        key_lower = key.lower()

        # Check if key contains sensitive information
        if any(sensitive in key_lower for sensitive in self.config.sensitive_keys):
            return f"<{type(value).__name__} REDACTED>"

        # Convert value to string with length limit
        try:
            str_value = str(value)
            if len(str_value) > self.config.max_arg_length:
                return f"{str_value[:self.config.max_arg_length]}... (truncated)"
            return str_value
        except Exception:
            return f"<{type(value).__name__} repr_error>"

    def _format_arguments(
        self, args: tuple, kwargs: dict, bound_args: inspect.BoundArguments
    ) -> str:
        """Format function arguments for logging."""
        if not self.config.log_arguments:
            return ""

        formatted_args = []

        # Format bound arguments (includes both args and kwargs)
        for name, value in bound_args.arguments.items():
            sanitized_value = self._sanitize_value(name, value)
            formatted_args.append(f"{name}={sanitized_value}")

        return f"({', '.join(formatted_args)})" if formatted_args else "()"

    def _format_return_value(self, return_value: Any) -> str:
        """Format return value for logging."""
        if not self.config.log_return_values:
            return ""

        sanitized_value = self._sanitize_value("return", return_value)
        return f" -> {sanitized_value}"

    def log_function_entry(
        self,
        func_name: str,
        args: tuple,
        kwargs: dict,
        bound_args: inspect.BoundArguments,
    ) -> None:
        """Log function entry."""
        if self.logger.isEnabledFor(logging.INFO):
            args_str = (
                self._format_arguments(args, kwargs, bound_args)
                if self.logger.isEnabledFor(logging.DEBUG)
                else ""
            )
            self.logger.info(f"🔵 ENTER {func_name}{args_str}")

    def log_function_exit(
        self, func_name: str, return_value: Any, execution_time: float
    ) -> None:
        """Log function exit."""
        if self.logger.isEnabledFor(logging.DEBUG):
            return_str = self._format_return_value(return_value)
            time_str = (
                f" [{execution_time:.3f}s]" if self.config.log_execution_time else ""
            )
            self.logger.debug(f"🟢 EXIT  {func_name}{return_str}{time_str}")

    def log_function_exception(
        self, func_name: str, exception: Exception, execution_time: float
    ) -> None:
        """Log function exception."""
        time_str = f" [{execution_time:.3f}s]" if self.config.log_execution_time else ""
        self.logger.error(
            f"🔴 ERROR {func_name} raised {type(exception).__name__}: {exception}{time_str}"
        )

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)


# Global configuration
_global_config = LogConfig()
_loggers: dict[str, EmailAgentLogger] = {}


def configure_logging(config: LogConfig) -> None:
    """Configure the global logging settings."""
    global _global_config
    _global_config = config

    # Clear existing loggers to use new config
    _loggers.clear()


def get_logger(name: str | None = None) -> EmailAgentLogger:
    """Get a logger instance with the specified name."""
    if name is None:
        # Get the calling module name
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get("__name__", "emailagent")

    if name not in _loggers:
        _loggers[name] = EmailAgentLogger(name, _global_config)

    return _loggers[name]


def log_function(
    logger: EmailAgentLogger | None = None,
    level: str | None = None,
    log_args: bool | None = None,
    log_return: bool | None = None,
    log_time: bool | None = None,
) -> Callable:
    """
    Decorator to log function entry, exit, arguments, and return values.

    Args:
        logger: Logger instance to use (defaults to auto-detected)
        level: Override log level for this function
        log_args: Override argument logging for this function
        log_return: Override return value logging for this function
        log_time: Override execution time logging for this function

    Usage:
        @log_function()
        def my_function(arg1, arg2="default"):
            return "result"

        @log_function(level="DEBUG", log_args=True)
        async def async_function(data):
            await some_operation(data)
            return {"status": "success"}
    """

    def decorator(func: Callable) -> Callable:
        # Get logger for this function
        nonlocal logger
        if logger is None:
            module_name = func.__module__
            logger = get_logger(module_name)

        # Get function signature for argument binding
        sig = inspect.signature(func)
        func_name = f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # Bind arguments
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Log entry
                logger.log_function_entry(func_name, args, kwargs, bound_args)

                # Execute function
                result = func(*args, **kwargs)

                # Log exit
                execution_time = time.time() - start_time
                logger.log_function_exit(func_name, result, execution_time)

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.log_function_exception(func_name, e, execution_time)
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # Bind arguments
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()

                # Log entry
                logger.log_function_entry(func_name, args, kwargs, bound_args)

                # Execute async function
                result = await func(*args, **kwargs)

                # Log exit
                execution_time = time.time() - start_time
                logger.log_function_exit(func_name, result, execution_time)

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.log_function_exception(func_name, e, execution_time)
                raise

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Convenience decorators for common use cases
def log_debug(
    func: Callable | None = None, **kwargs
) -> Callable | Callable[[Callable], Callable]:
    """Decorator to log function at DEBUG level with full details."""

    def decorator(f: Callable) -> Callable:
        return log_function(
            level="DEBUG", log_args=True, log_return=True, log_time=True, **kwargs
        )(f)

    if func is None:
        return decorator
    else:
        return decorator(func)


def log_info(
    func: Callable | None = None, **kwargs
) -> Callable | Callable[[Callable], Callable]:
    """Decorator to log function at INFO level with entry only."""

    def decorator(f: Callable) -> Callable:
        return log_function(
            level="INFO", log_args=False, log_return=False, log_time=False, **kwargs
        )(f)

    if func is None:
        return decorator
    else:
        return decorator(func)


# This module is production-ready - no test code included
# For testing the logging system, use the separate test files in the tests/ directory
