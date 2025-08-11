"""
Logging configuration for LLM-powered monitoring application.
Supports dual-mode logging: debug (rich console) vs normal (structured JSON).
"""
import json
import logging
import logging.handlers
import os
import sys
import threading
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "thread_id": threading.current_thread().name,
        }
        
        # Add extra fields if present
        if hasattr(record, 'component'):
            log_entry['component'] = record.component
        if hasattr(record, 'workflow_phase'):
            log_entry['workflow_phase'] = record.workflow_phase
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        if hasattr(record, 'workload_name'):
            log_entry['workload_name'] = record.workload_name
        if hasattr(record, 'namespace'):
            log_entry['namespace'] = record.namespace
        if hasattr(record, 'status_code'):
            log_entry['status_code'] = record.status_code
        if hasattr(record, 'method'):
            log_entry['method'] = record.method
        if hasattr(record, 'path'):
            log_entry['path'] = record.path
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


def setup_logging() -> None:
    """Setup logging configuration based on environment variables."""
    debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    enable_file_logging = os.getenv('ENABLE_FILE_LOGGING', 'false').lower() == 'true'
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    if debug_mode and not enable_file_logging:
        # Pure debug mode: minimal console logging (rich output handled by printer)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)  # Only warnings/errors
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    elif debug_mode and enable_file_logging:
        # Hybrid mode: minimal console + structured file logging
        setup_hybrid_logging(log_level)
    else:
        # Normal mode: structured logging (stdout + optional file)
        setup_structured_logging(log_level, enable_file_logging)


def setup_structured_logging(log_level: str, enable_file_logging: bool = True) -> None:
    """Setup structured JSON logging for normal mode."""
    root_logger = logging.getLogger()
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler (rotating) - optional
    if enable_file_logging:
        setup_file_logging(log_level)


def setup_hybrid_logging(log_level: str) -> None:
    """Setup hybrid mode: minimal console + structured file logging."""
    root_logger = logging.getLogger()
    
    # Minimal console handler for warnings/errors only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with structured logging
    setup_file_logging(log_level)


def setup_file_logging(log_level: str) -> None:
    """Setup file logging with rotation."""
    root_logger = logging.getLogger()
    
    try:
        log_dir = '/tmp/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, 'monitoring.log')
        max_bytes = int(os.getenv('LOG_MAX_MB', '10')) * 1024 * 1024
        backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, log_level, logging.INFO))
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
        
        # Log successful file logging setup
        logger = logging.getLogger(__name__)
        logger.info("File logging configured", extra={
            'component': 'logging_config',
            'operation': 'setup',
            'log_file': log_file,
            'max_mb': max_bytes // (1024 * 1024),
            'backup_count': backup_count
        })
        
    except Exception as e:
        # Fallback gracefully if file logging fails
        logger = logging.getLogger(__name__)
        logger.warning(f"File logging setup failed: {e}", extra={
            'component': 'logging_config',
            'operation': 'fallback'
        })


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def is_debug_mode() -> bool:
    """Check if running in debug mode."""
    return os.getenv('DEBUG_MODE', 'false').lower() == 'true'


def is_file_logging_enabled() -> bool:
    """Check if file logging is enabled."""
    return os.getenv('ENABLE_FILE_LOGGING', 'false').lower() == 'true'


def get_logging_mode() -> str:
    """Get the current logging mode as a descriptive string."""
    debug_mode = is_debug_mode()
    file_logging = is_file_logging_enabled()
    
    if debug_mode and file_logging:
        return "hybrid"  # Rich console + structured file
    elif debug_mode:
        return "debug"   # Rich console only
    elif file_logging:
        return "structured_with_file"  # JSON stdout + file
    else:
        return "structured_stdout_only"  # JSON stdout only


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs) -> None:
    """Log a message with additional context fields."""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, extra=kwargs)
