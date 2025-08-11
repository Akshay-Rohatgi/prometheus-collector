# Enhanced Tri-Mode Logging Implementation

This document describes the enhanced tri-mode logging system implemented for the LLM-Powered Monitoring application.

## Features

- **Tri-Mode Operation**: Choose between debug-only, hybrid, structured-with-file, or structured-stdout-only modes
- **Hybrid Mode**: Get both rich console output AND structured file logging simultaneously
- **Structured JSON Logging**: Production-ready structured logs with consistent field names
- **File Rotation**: Automatic log file rotation with configurable size and backup count
- **Sensitive Data Protection**: Automatic redaction of sensitive information like tokens and secrets
- **OpenTelemetry Ready**: Structured for future OpenTelemetry trace correlation
- **Backward Compatibility**: Existing `printer` module continues to work unchanged

## Configuration

Control logging behavior via environment variables:

```bash
# Logging mode control
DEBUG_MODE=true              # Enable rich console output
ENABLE_FILE_LOGGING=true     # Enable structured file logging

# Log level
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR

# File logging configuration
LOG_MAX_MB=10              # Max file size in MB before rotation
LOG_BACKUP_COUNT=5         # Number of backup files to keep
```

## Logging Modes

### Mode 1: Debug Only (Rich Console Only)
```bash
DEBUG_MODE=true ENABLE_FILE_LOGGING=false
```
- ✅ Beautiful rich console output with emojis
- ❌ No file logging
- 🎯 Perfect for: Local development and debugging

### Mode 2: Hybrid (Rich Console + Structured File)
```bash
DEBUG_MODE=true ENABLE_FILE_LOGGING=true
```
- ✅ Beautiful rich console output with emojis  
- ✅ Structured JSON logs written to file
- 🎯 Perfect for: Development with log analysis needs

### Mode 3: Structured with File (JSON Console + File)
```bash
DEBUG_MODE=false ENABLE_FILE_LOGGING=true
```
- ✅ Structured JSON output to console
- ✅ Structured JSON logs written to file  
- 🎯 Perfect for: Production with comprehensive logging

### Mode 4: Structured Stdout Only (JSON Console Only)
```bash
DEBUG_MODE=false ENABLE_FILE_LOGGING=false
```
- ✅ Structured JSON output to console
- ❌ No file logging
- 🎯 Perfect for: Containerized production (log forwarding)

## Usage

### Application Initialization

```python
import logs

# Initialize logging at application startup
logs.setup_logging()
logger = logs.get_logger(__name__)

# Check current mode
print(f"Logging mode: {logs.get_logging_mode()}")

logger.info("Application started", extra={
    'component': 'main',
    'operation': 'startup'
})
```

### Using the Printer Module (Works in All Modes)

```python
from printer import printer

# In debug-only mode: Rich console output only
# In hybrid mode: Rich console + structured file logs  
# In structured modes: JSON logs only
printer.info("Detecting workloads...")
printer.success("Operation completed!")
printer.warning("Manual verification needed")
printer.error("Connection failed")
printer.banner("Workflow Started")
```

### Direct Structured Logging

```python
from logs import get_logger, log_with_context

logger = get_logger(__name__)

# Basic structured log
logger.info("Workflow phase completed", extra={
    'component': 'ai_graphs',
    'operation': 'detect_workloads',
    'duration_ms': 1234,
    'workloads_found': 5
})

# Helper function for consistent logging
log_with_context(logger, 'info', 'K8s API call completed', 
                 component='k8s_client', 
                 operation='list_pods',
                 namespace='default',
                 pod_count=10)
```

## Log Output Examples

### Debug-Only Mode Output
```
 === Workflow Started === 
ℹ️  Detecting Kubernetes workloads...
✅ Operation completed successfully!
⚠️  Some workloads need verification  
🚨 Connection failed
```

### Hybrid Mode Output
**Console (Rich):**
```
 === Workflow Started === 
ℹ️  Detecting Kubernetes workloads...
✅ Operation completed successfully!
```

**File (/tmp/logs/monitoring.log):**
```json
{"timestamp": "2025-08-11T11:14:06.948715Z", "level": "INFO", "logger": "printer.printer", "message": "=== Workflow Started ===", "thread_id": "MainThread", "component": "printer", "operation": "banner"}
{"timestamp": "2025-08-11T11:14:06.949012Z", "level": "INFO", "logger": "printer.printer", "message": "Detecting Kubernetes workloads...", "thread_id": "MainThread", "component": "printer", "operation": "info"}
```

### Structured Mode Output
```json
{
  "timestamp": "2025-08-11T11:09:50.532391Z",
  "level": "INFO",
  "logger": "workflow_demo",
  "message": "API request received",
  "thread_id": "MainThread",
  "component": "api",
  "operation": "start_workflow",
  "method": "GET",
  "path": "/start"
}
```

## Structured Log Fields

### Standard Fields (always present)
- `timestamp`: ISO 8601 timestamp with timezone
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `logger`: Logger name (usually module name)
- `message`: Human-readable message
- `thread_id`: Thread name for concurrency tracking

### Optional Context Fields
- `component`: Application component (api, ai_graphs, k8s_client, etc.)
- `operation`: Specific operation being performed
- `workflow_phase`: Current workflow phase
- `duration_ms`: Operation duration in milliseconds
- `workload_name`: K8s workload name
- `namespace`: K8s namespace
- `status_code`: HTTP status code
- `method`: HTTP method
- `path`: Request path

## File Logging

In normal mode, logs are written to both stdout and `/tmp/logs/monitoring.log` with automatic rotation.

```bash
# View recent logs
tail -f /tmp/logs/monitoring.log

# View logs in JSON pretty format
tail /tmp/logs/monitoring.log | jq .

# Search for specific operations
grep '"operation":"detect_workloads"' /tmp/logs/monitoring.log | jq .
```

## Security Features

### Sensitive Data Protection

The logging system automatically redacts log messages containing sensitive keywords:
- token, secret, password, key, api_key
- bearer, authorization, auth

```python
logger.info("Processing API token xyz123")  
# Becomes: "[REDACTED] Attempted to log sensitive data containing 'token'"
```

## Integration with Existing Code

### API Routes
```python
@app.get("/start")
async def start_workflow():
    logger.info("Starting new workflow", extra={
        'component': 'api',
        'operation': 'start_workflow'
    })
    # ... rest of function
```

### Workflow Functions
```python
def detect_workloads(workflow: Workflow):
    start_time = time.time()
    logger.info("Starting workload detection", extra={
        'component': 'ai_graphs',
        'operation': 'detect_workloads',
        'workflow_phase': 'workload-detection'
    })
    
    try:
        # ... workload detection logic
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Workload detection completed", extra={
            'component': 'ai_graphs',
            'operation': 'detect_workloads',
            'duration_ms': duration_ms,
            'workloads_detected': len(workloads)
        })
    except Exception as e:
        logger.error(f"Workload detection failed: {e}", extra={
            'component': 'ai_graphs',
            'operation': 'detect_workloads_error'
        })
```

### K8s Operations
```python
def k8s_api_call():
    logger.info("K8s API call initiated", extra={
        'component': 'k8s_client',
        'operation': 'list_services',
        'namespace': namespace
    })
```

## Testing

Run the test scripts to verify all logging modes:

```bash
# Test all tri-mode configurations  
python3 test_enhanced_logging.py

# Test specific modes
DEBUG_MODE=true ENABLE_FILE_LOGGING=false python3 demo_logging.py     # Debug-only
DEBUG_MODE=true ENABLE_FILE_LOGGING=true python3 demo_logging.py      # Hybrid  
DEBUG_MODE=false ENABLE_FILE_LOGGING=true python3 demo_logging.py     # Structured+File
DEBUG_MODE=false ENABLE_FILE_LOGGING=false python3 demo_logging.py    # Structured-only

# Check current logging mode
python3 -c "import logs; logs.setup_logging(); print(f'Mode: {logs.get_logging_mode()}')"
```

## Future OpenTelemetry Integration

The structured logging is designed to integrate seamlessly with OpenTelemetry:

- `thread_id` can become trace correlation
- Consistent component/operation naming for span attributes  
- Duration tracking ready for span timing
- Error context preserved for span error reporting

## Deployment Considerations

### Container Environment
- Logs to stdout are captured by container runtime
- File logs require volume mount at `/tmp/logs`
- Set `DEBUG_MODE=false` for production

### Kubernetes Deployment
```yaml
env:
- name: DEBUG_MODE
  value: "false"                    # Use structured logging
- name: ENABLE_FILE_LOGGING  
  value: "false"                    # Stdout-only for container logs
- name: LOG_LEVEL  
  value: "INFO"

# For development/troubleshooting with file logs:
- name: ENABLE_FILE_LOGGING
  value: "true"
volumeMounts:
- name: logs
  mountPath: /tmp/logs
```

## Mode Selection Guide

| Use Case | DEBUG_MODE | ENABLE_FILE_LOGGING | Result |
|----------|------------|-------------------|---------|
| **Local Development** | `true` | `false` | Rich console only |
| **Development + Analysis** | `true` | `true` | Rich console + structured file |  
| **Production + File Logs** | `false` | `true` | JSON console + file |
| **Container Production** | `false` | `false` | JSON console only |

## Troubleshooting

### Common Issues

1. **File logging fails**: Check directory permissions for `/tmp/logs`
2. **No structured logs**: Verify `DEBUG_MODE=false` is set
3. **Missing context fields**: Use `extra={}` parameter in log calls
4. **Sensitive data in logs**: Check the sensitive data filter patterns

### Debug Commands

```bash
# Check log file location and size
ls -la /tmp/logs/

# Verify JSON format
tail /tmp/logs/monitoring.log | jq .

# Check environment variables
env | grep -E "(DEBUG_MODE|LOG_LEVEL)"

# Test logging configuration
python3 -c "import logs; logs.setup_logging(); logs.get_logger('test').info('test')"
```
