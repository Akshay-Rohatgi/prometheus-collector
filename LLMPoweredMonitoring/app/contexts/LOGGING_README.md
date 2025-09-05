# Logging Configuration and Best Practices

## Overview

The LLM-Powered Monitoring System implements a comprehensive structured logging system designed for production environments, debugging, and observability. The logging framework provides multiple modes of operation, sensitive data protection, and integration with monitoring systems.

## Architecture

### Logging Components

1. **Core Logger** (`logs/config.py`)
   - Centralized logging configuration
   - Multiple output formats and destinations
   - Performance monitoring integration
   - Security-aware log filtering

2. **Printer Module** (`printer/printer.py`)
   - User-facing output formatting
   - Rich console output for development
   - Progress indicators and status updates
   - Backward compatibility layer

3. **Structured Logging**
   - JSON-formatted logs for production
   - Consistent field naming and structure
   - Correlation IDs for request tracing
   - Machine-readable format for analysis

### Logging Modes

#### 1. Development Mode
```python
# Rich console output with detailed debugging
LOGGING_MODE = "debug"
LOG_LEVEL = "DEBUG"
CONSOLE_OUTPUT = True
FILE_OUTPUT = False
```

#### 2. Production Mode
```python
# Structured JSON logging to files and stdout
LOGGING_MODE = "structured"
LOG_LEVEL = "INFO"
CONSOLE_OUTPUT = True
FILE_OUTPUT = True
LOG_FORMAT = "json"
```

#### 3. Hybrid Mode
```python
# Both rich console and structured file logging
LOGGING_MODE = "hybrid"
LOG_LEVEL = "INFO"
CONSOLE_OUTPUT = True
FILE_OUTPUT = True
RICH_CONSOLE = True
```

## Configuration

### Environment Variables

```bash
# Primary logging configuration
LOGGING_MODE = "hybrid"              # Options: debug, hybrid, structured
LOG_LEVEL = "INFO"                   # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
CONSOLE_OUTPUT = "true"              # Enable/disable console output
FILE_OUTPUT = "true"                 # Enable/disable file output
LOG_FORMAT = "json"                  # Options: json, text
LOG_FILE_PATH = "logs/app.log"       # Log file location
LOG_MAX_SIZE = "10MB"                # Maximum log file size
LOG_BACKUP_COUNT = "5"               # Number of backup files to keep

# Advanced configuration
ENABLE_LOG_ROTATION = "true"         # Enable automatic log rotation
LOG_CORRELATION_ID = "true"          # Include correlation IDs
SENSITIVE_DATA_REDACTION = "true"    # Enable sensitive data filtering
PERFORMANCE_LOGGING = "true"         # Log performance metrics
```

### Configuration Examples

#### Development Environment
```yaml
# docker-compose.dev.yml
environment:
  LOGGING_MODE: "debug"
  LOG_LEVEL: "DEBUG"
  CONSOLE_OUTPUT: "true"
  FILE_OUTPUT: "false"
  RICH_CONSOLE: "true"
```

#### Production Environment
```yaml
# kubernetes deployment
env:
- name: LOGGING_MODE
  value: "structured"
- name: LOG_LEVEL
  value: "INFO"
- name: LOG_FORMAT
  value: "json"
- name: FILE_OUTPUT
  value: "true"
- name: LOG_FILE_PATH
  value: "/app/logs/app.log"
```

## Implementation Details

### Logger Initialization

```python
# logs/config.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        # Add performance metrics if available
        if hasattr(record, 'duration_ms'):
            log_entry["performance"] = {
                "duration_ms": record.duration_ms
            }
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry["request"] = {
                "id": record.request_id,
                "method": getattr(record, 'method', None),
                "path": getattr(record, 'path', None)
            }
        
        return json.dumps(log_entry)

def setup_logging():
    """Configure logging based on environment variables."""
    
    mode = os.getenv("LOGGING_MODE", "structured")
    level = os.getenv("LOG_LEVEL", "INFO")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    if mode == "debug":
        setup_debug_logging()
    elif mode == "hybrid":
        setup_hybrid_logging()
    elif mode == "structured":
        setup_structured_logging()
```

### Sensitive Data Protection

```python
class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from logs."""
    
    SENSITIVE_PATTERNS = [
        r'api[_-]?key["\s]*[:=]["\s]*([^"\s,}]+)',
        r'token["\s]*[:=]["\s]*([^"\s,}]+)',
        r'password["\s]*[:=]["\s]*([^"\s,}]+)',
        r'secret["\s]*[:=]["\s]*([^"\s,}]+)',
        r'authorization["\s]*[:=]["\s]*([^"\s,}]+)',
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log records."""
        
        message = record.getMessage()
        
        for pattern in self.SENSITIVE_PATTERNS:
            message = re.sub(
                pattern, 
                lambda m: m.group(0).replace(m.group(1), "[REDACTED]"),
                message,
                flags=re.IGNORECASE
            )
        
        # Update the record message
        record.msg = message
        record.args = ()
        
        return True
```

### Performance Logging

```python
import time
from functools import wraps

def log_performance(logger_name: str = None):
    """Decorator to log function performance metrics."""
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"Function {func.__name__} completed successfully",
                    extra={
                        "duration_ms": duration_ms,
                        "function": func.__name__,
                        "success": True
                    }
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                logger.error(
                    f"Function {func.__name__} failed: {str(e)}",
                    extra={
                        "duration_ms": duration_ms,
                        "function": func.__name__,
                        "success": False,
                        "error": str(e)
                    }
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                logger.info(
                    f"Function {func.__name__} completed successfully",
                    extra={"duration_ms": duration_ms}
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                logger.error(
                    f"Function {func.__name__} failed: {str(e)}",
                    extra={
                        "duration_ms": duration_ms,
                        "error": str(e)
                    }
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator
```

## Usage Patterns

### Basic Logging

```python
import logging

# Get logger for current module
logger = logging.getLogger(__name__)

# Standard log levels
logger.debug("Detailed debugging information")
logger.info("General information about application flow")
logger.warning("Warning about potential issues")
logger.error("Error occurred but application can continue")
logger.critical("Critical error that may cause application to stop")

# Structured logging with extra context
logger.info(
    "User workflow started",
    extra={
        "user_id": "user123",
        "workflow_type": "monitoring_setup",
        "correlation_id": "req-456"
    }
)
```

### Request Correlation

```python
import uuid
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar('correlation_id')

class CorrelationMiddleware:
    """FastAPI middleware to add correlation IDs."""
    
    async def __call__(self, request: Request, call_next):
        # Generate or extract correlation ID
        corr_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
        correlation_id.set(corr_id)
        
        # Add to response headers
        response = await call_next(request)
        response.headers['X-Correlation-ID'] = corr_id
        
        return response

class CorrelationFilter(logging.Filter):
    """Add correlation ID to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.correlation_id = correlation_id.get()
        except LookupError:
            record.correlation_id = None
        
        return True
```

### AI Agent Logging

```python
# AI agent specific logging
def log_agent_execution(agent_name: str, phase: str):
    """Log AI agent execution details."""
    
    logger = logging.getLogger(f"ai.agents.{agent_name}")
    
    logger.info(
        f"AI agent execution started",
        extra={
            "agent_name": agent_name,
            "phase": phase,
            "agent_type": "ai_execution"
        }
    )

# Usage in AI workflow
def detect_workloads(workflow: Workflow) -> dict:
    log_agent_execution("workload_detection", workflow.phase)
    
    try:
        result = execute_agent_logic()
        
        logger.info(
            "Workload detection completed",
            extra={
                "workloads_found": len(result.get("workloads", [])),
                "phase": workflow.phase
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            f"Workload detection failed: {str(e)}",
            extra={
                "phase": workflow.phase,
                "error_type": type(e).__name__
            }
        )
        raise
```

## Monitoring and Observability

### Log Analysis

```bash
# Filter logs by level
cat logs/app.log | jq 'select(.level == "ERROR")'

# Monitor performance metrics
cat logs/app.log | jq 'select(.performance.duration_ms > 1000)'

# Track specific workflows
cat logs/app.log | jq 'select(.correlation_id == "req-456")'

# Error rate analysis
cat logs/app.log | jq -r '.level' | sort | uniq -c
```

### Integration with Monitoring Systems

#### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
log_counter = Counter('app_logs_total', 'Total log entries', ['level'])
request_duration = Histogram('request_duration_seconds', 'Request duration')

class MetricsHandler(logging.Handler):
    """Send log metrics to Prometheus."""
    
    def emit(self, record: logging.LogRecord):
        log_counter.labels(level=record.levelname.lower()).inc()
        
        if hasattr(record, 'duration_ms'):
            request_duration.observe(record.duration_ms / 1000)
```

#### Azure Monitor Integration
```python
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Azure Monitor
configure_azure_monitor(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
)

class AzureHandler(logging.Handler):
    """Send logs to Azure Application Insights."""
    
    def emit(self, record: logging.LogRecord):
        # Send structured logs to Azure Monitor
        pass
```

## Best Practices

### 1. Structured Logging
- Use consistent field names across all log entries
- Include context information (user_id, request_id, correlation_id)
- Use appropriate log levels based on importance
- Include performance metrics for critical operations

### 2. Security Considerations
- Always enable sensitive data redaction in production
- Avoid logging sensitive information (passwords, tokens, keys)
- Use correlation IDs instead of user-identifiable information when possible
- Regularly review logs for unintended data exposure

### 3. Performance Optimization
- Use appropriate log levels to control verbosity
- Implement log buffering for high-throughput scenarios
- Consider async logging for performance-critical applications
- Monitor log file sizes and implement rotation

### 4. Debugging and Development
- Use DEBUG level extensively during development
- Include stack traces for exceptions
- Log entry and exit points for complex functions
- Use rich console output for better developer experience

### 5. Production Operations
- Implement centralized log aggregation
- Set up alerts for ERROR and CRITICAL log levels
- Monitor log volume and performance impact
- Regularly archive or clean up old log files

This comprehensive logging system provides the foundation for effective monitoring, debugging, and observability in the LLM-Powered Monitoring System.
