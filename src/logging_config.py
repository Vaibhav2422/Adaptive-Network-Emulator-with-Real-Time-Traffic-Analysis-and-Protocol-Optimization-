"""
Logging infrastructure for the Adaptive Network Emulator.
Provides structured JSON logging with rotation, hierarchical loggers, and context tracking.
"""
import os
import json
import logging
import logging.handlers
import threading
from datetime import datetime
from typing import Dict, Any, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "thread_id": threading.get_ident(),
            "thread_name": threading.current_thread().name,
        }
        
        # Add context if available
        if hasattr(record, "context"):
            log_data["context"] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "message", "pathname", "process", "processName",
                          "relativeCreated", "thread", "threadName", "exc_info",
                          "exc_text", "stack_info", "context"]:
                log_data[key] = value
        
        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Filter that adds context information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to the log record."""
        if self.context:
            record.context = self.context
        return True


class LoggerManager:
    """Manages hierarchical loggers for the emulator."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO",
                 log_to_file: bool = True, max_bytes: int = 100 * 1024 * 1024,
                 backup_count: int = 10):
        """
        Initialize the logger manager.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_to_file: Whether to write logs to files
            max_bytes: Maximum size per log file (default 100MB)
            backup_count: Number of backup files to keep (default 10)
        """
        self.log_dir = log_dir
        self.log_level = getattr(logging, log_level.upper())
        self.log_to_file = log_to_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.loggers: Dict[str, logging.Logger] = {}
        
        # Create log directory if it doesn't exist
        if self.log_to_file:
            os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up root logger
        self._setup_root_logger()
    
    def _setup_root_logger(self) -> None:
        """Set up the root logger."""
        root_logger = logging.getLogger("emulator")
        root_logger.setLevel(self.log_level)
        root_logger.handlers.clear()
        
        # Console handler with simple format
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with JSON format and rotation
        if self.log_to_file:
            log_file = os.path.join(self.log_dir, "emulator.log")
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(file_handler)
        
        self.loggers["root"] = root_logger
    
    def get_logger(self, name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """
        Get or create a logger with the specified name.
        
        Args:
            name: Logger name (e.g., "emulator.physical_layer", "emulator.node.node1")
            context: Optional context dictionary to add to all log messages
        
        Returns:
            Logger instance
        """
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Add context filter if provided
        if context:
            logger.addFilter(ContextFilter(context))
        
        # Create separate log file for this logger if enabled
        if self.log_to_file and name != "emulator":
            # Create a sanitized filename from the logger name
            filename = name.replace(".", "_") + ".log"
            log_file = os.path.join(self.log_dir, filename)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        
        self.loggers[name] = logger
        return logger
    
    def get_system_logger(self) -> logging.Logger:
        """Get the system-level logger."""
        return self.get_logger("emulator.system")
    
    def get_layer_logger(self, layer_name: str) -> logging.Logger:
        """
        Get a logger for a specific protocol layer.
        
        Args:
            layer_name: Layer name (e.g., "physical", "mac", "data_link", "network", "transport", "application")
        
        Returns:
            Logger instance
        """
        return self.get_logger(f"emulator.{layer_name}_layer")
    
    def get_node_logger(self, node_id: str) -> logging.Logger:
        """
        Get a logger for a specific node.
        
        Args:
            node_id: Node identifier
        
        Returns:
            Logger instance
        """
        return self.get_logger(f"emulator.node.{node_id}", context={"node_id": node_id})
    
    def set_level(self, level: str) -> None:
        """
        Change the logging level for all loggers.
        
        Args:
            level: New logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_level = getattr(logging, level.upper())
        for logger in self.loggers.values():
            logger.setLevel(self.log_level)
            for handler in logger.handlers:
                handler.setLevel(self.log_level)
    
    def shutdown(self) -> None:
        """Shutdown all loggers and close handlers."""
        for logger in self.loggers.values():
            for handler in logger.handlers:
                handler.close()
                logger.removeHandler(handler)
        logging.shutdown()


# Global logger manager instance
_logger_manager: Optional[LoggerManager] = None


def initialize_logging(log_dir: str = "logs", log_level: str = "INFO",
                      log_to_file: bool = True) -> LoggerManager:
    """
    Initialize the global logging system.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        log_to_file: Whether to write logs to files
    
    Returns:
        LoggerManager instance
    """
    global _logger_manager
    _logger_manager = LoggerManager(log_dir, log_level, log_to_file)
    return _logger_manager


def get_logger_manager() -> LoggerManager:
    """
    Get the global logger manager instance.
    
    Returns:
        LoggerManager instance
    
    Raises:
        RuntimeError: If logging hasn't been initialized
    """
    if _logger_manager is None:
        raise RuntimeError("Logging not initialized. Call initialize_logging() first.")
    return _logger_manager
