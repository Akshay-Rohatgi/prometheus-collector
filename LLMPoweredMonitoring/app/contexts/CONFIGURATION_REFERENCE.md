# Configuration Reference

## Overview

This document provides comprehensive configuration options for the LLM-Powered Monitoring System, including environment variables, model settings, workflow parameters, and deployment configurations.

## Environment Variables

### Core Application Configuration
```bash
# Application Runtime
HOST=0.0.0.0                    # Server bind address
PORT=8000                       # Server port
DEBUG=false                     # Debug mode (enables rich console logging)
LOG_LEVEL=INFO                  # Logging level (DEBUG, INFO, WARNING, ERROR)

# Kubernetes Configuration
K8S_CONFIG_PATH=/path/to/kubeconfig  # Kubernetes configuration file path
K8S_CONTEXT=cluster-context          # Kubernetes context name (optional)

# Workflow Configuration
MAX_EVALUATION_ROUNDS=3              # Maximum plan evaluation iterations
OSS_WORKLOAD_EMOJI=📦               # Display emoji for OSS workloads

# Workflow Lifecycle Management
MAX_WORKFLOWS=7                      # Maximum concurrent workflows
WORKFLOW_TTL_COMPLETED=600           # TTL for completed workflows (seconds)
WORKFLOW_TTL_FAILED=900              # TTL for failed workflows (seconds) 
WORKFLOW_TTL_CANCELLED=300           # TTL for cancelled workflows (seconds)
WORKFLOW_INACTIVE_TTL=1800           # TTL for idle active workflows (seconds)
WORKFLOW_CLEANUP_INTERVAL=60         # Background cleanup frequency (seconds)
EVICTION_POLICY=lru                  # Eviction policy: "lru" or "reject"
```

### Azure OpenAI Configuration
**Primary Configuration** (`ai/env/.env`):
```bash
# Azure OpenAI Primary Endpoint
RASHMI_AZURE_OPENAI_API_KEY=your-primary-key
AZURE_OPENAI_ENDPOINT=https://rashmi-openai.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Azure OpenAI Secondary Endpoint (GPT-5)
AKSHAY_AZURE_OPENAI_API_KEY=your-secondary-key
AKSHAY_AZURE_OPENAI_ENDPOINT=https://t-arohatgi-5211-resource.cognitiveservices.azure.com/

# Fallback Configuration
OPENAI_KEY=your-openai-api-key       # Fallback API key
OPENAI_API_BASE=https://api.openai.com/v1  # Fallback endpoint
```

### GitHub Integration
**GitHub Configuration** (`ai/utils/env/.env`):
```bash
# GitHub API Access for Chart Repository Integration
GITHUB_TOKEN=your-github-token       # GitHub personal access token
GITHUB_USER=your-github-username     # GitHub username

# Repository Configuration
GITHUB_ORG=prometheus-community      # Default organization for charts
GITHUB_REPO=helm-charts             # Default repository name
```

### External Dependencies
```bash
# Awesome Prometheus Alerts
AWESOME_ALERTS_BASE_PATH=/opt/awesome-prometheus-alerts/dist/rules

# Helm Configuration
HELM_REPO_CACHE_DIR=/tmp/helm-cache
HELM_CONFIG_HOME=/tmp/helm-config

# Tool Paths (optional overrides)
KUBECTL_PATH=/usr/local/bin/kubectl
HELM_PATH=/usr/local/bin/helm
```

## Model Configuration

### Model Definitions
**File**: `ai/models.py`

```python
# Azure OpenAI Model Configurations
models = {
    "o3": {
        "azure_deployment": "o3",
        "api_version": "2024-12-01-preview",
        "azure_endpoint": "https://rashmi-openai.openai.azure.com/",
        "temperature": 0.0,  # Deterministic for reasoning
        "use_case": "Advanced reasoning and complex decision making"
    },
    
    "gpt-4o": {
        "azure_deployment": "gpt-4o", 
        "api_version": "2024-12-01-preview",
        "azure_endpoint": "https://rashmi-openai.openai.azure.com/",
        "temperature": 0.3,  # Balanced creativity and consistency
        "use_case": "General purpose, evaluation, tool calling"
    },
    
    "gpt-4.1": {
        "azure_deployment": "gpt-4.1",
        "api_version": "2024-12-01-preview", 
        "azure_endpoint": "https://rashmi-openai.openai.azure.com/",
        "temperature": 0.3,
        "use_case": "Legacy compatibility and fallback"
    },
    
    "gpt-5": {
        "azure_deployment": "gpt-5",
        "api_version": "2024-12-01-preview",
        "azure_endpoint": "https://t-arohatgi-5211-resource.cognitiveservices.azure.com/",
        "temperature": 0.3,
        "reasoning_effort": "minimal",  # GPT-5 specific parameter
        "use_case": "Complex monitoring plan generation"
    }
}
```

### Model Selection Strategy
```python
# Agent-specific model assignments
AGENT_MODEL_MAPPING = {
    "workload_detection": "gpt-4o",           # Reliable detection
    "oss_detection": "gpt-4o",               # Pattern recognition
    "plan_generation": "gpt-5",              # Complex reasoning
    "plan_evaluation": "gpt-4o",             # Critical analysis
    "plan_structuring": "gpt-4o",            # Format conversion
    "dashboard_recommendation": "gpt-4o",     # Information retrieval
    "alerting_rules": "gpt-4o"               # Rule generation
}
```

### Model Parameters
```python
# Fine-tuning parameters for different use cases
MODEL_PARAMETERS = {
    "plan_generation": {
        "temperature": 0.3,        # Balanced creativity
        "max_tokens": 4000,        # Long-form content
        "top_p": 0.9,             # Nucleus sampling
        "frequency_penalty": 0.1,  # Reduce repetition
        "presence_penalty": 0.1    # Encourage diversity
    },
    
    "evaluation": {
        "temperature": 0.1,        # More deterministic
        "max_tokens": 2000,        # Focused responses
        "top_p": 0.8,             # More focused sampling
        "frequency_penalty": 0.0,  # No repetition penalty
        "presence_penalty": 0.0    # No presence penalty
    },
    
    "tool_calling": {
        "temperature": 0.0,        # Deterministic for accuracy
        "max_tokens": 1000,        # Structured responses
        "tool_choice": "auto",     # Automatic tool selection
        "parallel_tool_calls": True # Enable parallel execution
    }
}
```

## Workflow Configuration

### Phase Configuration
**File**: `core/workflow.py`

```python
# Workflow phase definitions
WORKFLOW_PHASES = [
    "not-started",
    "workload-detection", 
    "workload-selection",
    "monitoring-plan-generation",
    "monitoring-plan-evaluation",
    "deployment-confirmation", 
    "dashboard-recommendation",
    "alerting-rules-recommendation",
    "completed",
    "cancelled",
    "failed"
]

# Phase transition rules
PHASE_TRANSITIONS = {
    "not-started": ["workload-detection"],
    "workload-detection": ["workload-selection"],
    "workload-selection": ["monitoring-plan-generation"],
    "monitoring-plan-generation": ["monitoring-plan-evaluation"],
    "monitoring-plan-evaluation": ["deployment-confirmation", "monitoring-plan-generation"],  # Can retry
    "deployment-confirmation": ["dashboard-recommendation"],
    "dashboard-recommendation": ["alerting-rules-recommendation"],
    "alerting-rules-recommendation": ["completed"]
}
```

### Evaluation Configuration
```python
# Plan evaluation settings
EVALUATION_CONFIG = {
    "max_rounds": 3,                    # Maximum evaluation iterations
    "auto_approve_after_max": True,     # Auto-approve after max rounds
    "evaluation_timeout": 300,          # Timeout in seconds
    "critic_model": "gpt-4o",          # Model for evaluation
    "improvement_model": "gpt-5",       # Model for plan improvement
    
    # Evaluation criteria weights
    "criteria_weights": {
        "technical_accuracy": 0.3,
        "azure_compatibility": 0.3,
        "completeness": 0.2,
        "best_practices": 0.2
    }
}
```

### Agent Configuration
```python
# Agent-specific settings
AGENT_CONFIG = {
    "workload_detection": {
        "timeout": 60,
        "retry_attempts": 3,
        "namespace_filters": ["kube-system", "kube-public", "kube-node-lease"],
        "exclude_patterns": ["kubernetes", "metrics-server"]
    },
    
    "plan_generation": {
        "timeout": 300,
        "retry_attempts": 2,
        "tool_timeout": 30,
        "max_tool_calls": 10,
        "enable_chart_validation": True
    },
    
    "plan_evaluation": {
        "timeout": 180,
        "retry_attempts": 1,
        "validation_depth": "comprehensive",
        "azure_specific_checks": True
    }
}
```

## Workflow Lifecycle Management

The system includes comprehensive workflow lifecycle management to prevent memory leaks and ensure optimal performance under sustained usage.

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MAX_WORKFLOWS` | `7` | Maximum number of concurrent workflows before eviction |
| `WORKFLOW_TTL_COMPLETED` | `600` (10 min) | Time-to-live for completed workflows |
| `WORKFLOW_TTL_FAILED` | `900` (15 min) | Time-to-live for failed workflows |
| `WORKFLOW_TTL_CANCELLED` | `300` (5 min) | Time-to-live for cancelled workflows |
| `WORKFLOW_INACTIVE_TTL` | `1800` (30 min) | Time-to-live for idle active workflows |
| `WORKFLOW_CLEANUP_INTERVAL` | `60` (1 min) | Background cleanup task frequency |
| `EVICTION_POLICY` | `lru` | Eviction strategy: `lru` or `reject` |

### Eviction Strategy

The system uses a phased eviction approach when capacity is reached:

1. **TTL-based cleanup**: Remove workflows that have exceeded their phase-specific TTL
2. **Completed workflows**: Evict completed/cancelled/failed workflows by LRU order  
3. **Inactive workflows**: Remove inactive non-terminal workflows
4. **Idle active workflows**: Force-cancel and evict active workflows idle beyond `WORKFLOW_INACTIVE_TTL`

### Monitoring Endpoints

#### `/metrics/workflows`
Returns comprehensive workflow statistics:

```json
{
  "capacity": {
    "current": 6,
    "maximum": 7,
    "utilization_percent": 85.7,
    "available": 1
  },
  "phases": {
    "monitoring-plan-generation": 12,
    "completed": 15,
    "workload-selection": 8,
    "failed": 2
  },
  "activity": {
    "active": 25,
    "inactive": 20,
    "expired": 3
  },
  "age_statistics": {
    "oldest_seconds": 1800,
    "youngest_seconds": 45,
    "percentiles": {
      "p50": 320,
      "p90": 980,
      "p95": 1250,
      "p99": 1690
    }
  },
  "configuration": {
    "ttl_completed": 600,
    "ttl_failed": 900,
    "ttl_cancelled": 300,
    "inactive_ttl": 1800,
    "cleanup_interval": 60,
    "eviction_policy": "lru"
  },
  "timestamp": "2025-09-10T14:30:15.123456"
}
```

#### Capacity Management

When `EVICTION_POLICY=reject`, the system returns HTTP 429 if no workflows can be safely evicted:
```json
{
  "detail": "Workflow capacity reached; please try again later"
}
```

With `EVICTION_POLICY=lru` (default), the system will force-evict the oldest workflow as a last resort.

### Production Recommendations

- **High Traffic**: Increase `MAX_WORKFLOWS` to 50-100
- **Memory Constrained**: Keep `MAX_WORKFLOWS` at 7 or lower, decrease TTL values
- **Long-Running Workflows**: Increase `WORKFLOW_INACTIVE_TTL` to 3600s (1 hour)
- **Monitoring**: Set up alerts on `/metrics/workflows` utilization > 80%

### Application Lifespan

The API uses FastAPI's modern lifespan context instead of deprecated `@app.on_event` hooks. All workflow housekeeping initialization and teardown occur within the lifespan context manager. This provides:

- **Clean startup/shutdown**: Unified lifecycle management in one place
- **No deprecation warnings**: Uses current FastAPI best practices
- **Better testing support**: Compatible with modern ASGI tooling
- **Graceful shutdown**: Proper task cancellation and cleanup

The housekeeping task starts automatically on application startup and is cleanly cancelled during shutdown. No operator intervention is required.

## Logging Configuration

### Logging Levels and Formats
**File**: `logs/config.py`

```python
# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    
    "formatters": {
        "json": {
            "class": "logs.config.JSONFormatter",
            "format": "%(message)s"
        },
        "rich": {
            "class": "rich.logging.RichHandler",
            "show_time": True,
            "show_path": True,
            "rich_tracebacks": True
        }
    },
    
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "json",
            "stream": "sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": "logs/application.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    
    "loggers": {
        "": {  # Root logger
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "ai.graphs": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "api.routes": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}
```

### Structured Logging Fields
```python
# Standard log entry structure
LOG_ENTRY_SCHEMA = {
    "timestamp": "ISO 8601 timestamp",
    "level": "Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    "logger": "Logger name (module.function)",
    "message": "Human-readable message",
    "component": "System component (ai_graphs, api, k8s_client)",
    "operation": "Specific operation being performed",
    "workflow_phase": "Current workflow phase",
    "thread_id": "Workflow thread identifier",
    "duration_ms": "Operation duration in milliseconds",
    "workload_name": "Target workload name",
    "namespace": "Kubernetes namespace",
    "error_type": "Exception type for errors",
    "error_message": "Exception message for errors"
}
```

## Kubernetes Configuration

### RBAC Configuration
```yaml
# Required cluster permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: llm-powered-monitoring
rules:
# Service discovery
- apiGroups: [""]
  resources: ["services", "endpoints", "pods", "namespaces"]
  verbs: ["get", "list", "watch"]

# Workload analysis
- apiGroups: ["apps"] 
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch"]

# Monitoring resource management
- apiGroups: ["monitoring.coreos.com", "azmonitoring.coreos.com"]
  resources: ["servicemonitors", "prometheusrules", "podmonitors"]
  verbs: ["create", "get", "list", "watch", "update", "patch", "delete"]

# Configuration management
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
```

### Service Account Configuration
```yaml
# Service account for in-cluster execution
apiVersion: v1
kind: ServiceAccount
metadata:
  name: llm-powered-monitoring-sa
  namespace: llm-powered-monitoring
  annotations:
    azure.workload.identity/client-id: "your-client-id"  # For Azure Workload Identity
automountServiceAccountToken: true
```

### Network Configuration
```python
# Network and security settings
NETWORK_CONFIG = {
    "allowed_namespaces": ["production", "staging", "development"],
    "excluded_namespaces": ["kube-system", "kube-public", "kube-node-lease"],
    "service_discovery_timeout": 30,
    "api_request_timeout": 60,
    "max_concurrent_requests": 10
}
```

## Azure Integration Configuration

### Azure Managed Prometheus
```python
# Azure-specific configuration
AZURE_CONFIG = {
    "managed_prometheus": {
        "api_version": "azmonitoring.coreos.com/v1",  # Required for Azure
        "default_scrape_interval": "30s",
        "default_scrape_timeout": "10s",
        "metric_relabeling": True,
        "honor_labels": False
    },
    
    "workload_identity": {
        "enabled": True,
        "client_id_annotation": "azure.workload.identity/client-id",
        "tenant_id": "your-tenant-id"
    },
    
    "container_registry": {
        "registry": "mcr.microsoft.com",
        "repository": "azuremonitor/containerinsights/cidev/prometheus-collector/images",
        "tag": "llm-powered-monitoring-6"
    }
}
```

### Azure OpenAI Service Configuration
```python
# Azure OpenAI service settings
AZURE_OPENAI_CONFIG = {
    "retry_policy": {
        "max_retries": 3,
        "backoff_factor": 2,
        "status_forcelist": [429, 500, 502, 503, 504]
    },
    
    "rate_limiting": {
        "requests_per_minute": 60,
        "tokens_per_minute": 150000,
        "concurrent_requests": 5
    },
    
    "content_filtering": {
        "enable_content_filter": True,
        "filter_level": "medium"
    }
}
```

## Deployment Configuration

### Container Configuration
```python
# Container runtime settings
CONTAINER_CONFIG = {
    "resources": {
        "requests": {
            "cpu": "200m",
            "memory": "512Mi"
        },
        "limits": {
            "cpu": "1000m", 
            "memory": "2Gi"
        }
    },
    
    "health_checks": {
        "liveness_probe": {
            "path": "/",
            "port": 8000,
            "initial_delay_seconds": 30,
            "period_seconds": 10,
            "timeout_seconds": 5,
            "failure_threshold": 3
        },
        "readiness_probe": {
            "path": "/",
            "port": 8000,
            "initial_delay_seconds": 5,
            "period_seconds": 5,
            "timeout_seconds": 3,
            "failure_threshold": 3
        }
    },
    
    "security_context": {
        "run_as_non_root": True,
        "run_as_user": 1000,
        "fs_group": 1000,
        "read_only_root_filesystem": False,  # Required for tool execution
        "allow_privilege_escalation": False
    }
}
```

### Ingress Configuration
```yaml
# Ingress controller configuration
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llm-powered-monitoring
  namespace: llm-powered-monitoring
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/proxy-body-size: "16m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - monitoring-automation.your-domain.com
    secretName: monitoring-automation-tls
  rules:
  - host: monitoring-automation.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: llm-powered-monitoring
            port:
              number: 80
```

## Development Configuration

### Local Development Settings
```bash
# Development environment variables
export DEBUG=true
export LOG_LEVEL=DEBUG
export K8S_CONFIG_PATH="$HOME/.kube/config"
export MAX_EVALUATION_ROUNDS=2  # Faster iteration in dev

# Development model configuration (use cheaper models)
export DEVELOPMENT_MODE=true
export DEV_MODEL_OVERRIDE="gpt-4o"  # Use single model for all operations
```

### Testing Configuration
```python
# Test environment settings
TEST_CONFIG = {
    "mock_kubernetes": True,
    "mock_openai": False,  # Use real AI for evaluation tests
    "test_data_path": "tests/fixtures",
    "test_timeout": 600,   # 10 minutes for comprehensive tests
    
    "evaluation_metrics": {
        "oss_detection_threshold": 0.8,
        "plan_coherence_threshold": 0.7,
        "technical_correctness_threshold": 0.8,
        "azure_compatibility_threshold": 0.9
    }
}
```

## Security Configuration

### Secret Management
```yaml
# Secret configuration patterns
apiVersion: v1
kind: Secret
metadata:
  name: openai-secrets
  namespace: llm-powered-monitoring
type: Opaque
stringData:
  .env: |
    RASHMI_AZURE_OPENAI_API_KEY=sk-...
    AKSHAY_AZURE_OPENAI_API_KEY=sk-...
    OPENAI_KEY=sk-...

---
apiVersion: v1
kind: Secret
metadata:
  name: github-secrets
  namespace: llm-powered-monitoring
type: Opaque
stringData:
  .env: |
    GITHUB_TOKEN=ghp_...
    GITHUB_USER=username
```

### Security Policies
```python
# Security configuration
SECURITY_CONFIG = {
    "api_rate_limiting": {
        "requests_per_minute": 100,
        "burst_limit": 20
    },
    
    "command_execution": {
        "allowed_commands": ["kubectl", "helm"],
        "command_timeout": 300,
        "shell_injection_protection": True,
        "log_commands": True
    },
    
    "data_protection": {
        "mask_secrets_in_logs": True,
        "encrypt_workflow_state": False,  # Future enhancement
        "audit_all_operations": True
    }
}
```

This configuration reference provides comprehensive coverage of all configurable aspects of the LLM-Powered Monitoring System, enabling precise customization for different environments and use cases.
