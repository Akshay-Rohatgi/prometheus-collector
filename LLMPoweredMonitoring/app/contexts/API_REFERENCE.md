# API Reference and Integration Guide

## Overview

The system exposes a RESTful API built with FastAPI for workflow management and monitoring automation. This document provides comprehensive API documentation with real endpoint implementations, error handling, and integration examples.

## Base Configuration

### Server Setup
```python
# FastAPI application configuration (api/routes.py)
app = FastAPI(
    title="LLM-Powered Monitoring System", 
    description="Automated Kubernetes monitoring deployment with AI agents",
    version="1.0.0"
)

# Async-safe workflow management
_workflows: Dict[str, WorkflowStatus] = {}
_workflow_graphs: Dict[str, any] = {}
```

### Base URL Structure
```
Production:  https://monitoring-automation.your-domain.com
Development: http://localhost:8000
Local:       http://127.0.0.1:8000
```

### Request/Response Logging
All requests are logged with structured information:
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("HTTP request received", extra={
        'component': 'api',
        'operation': 'request_start', 
        'method': request.method,
        'path': str(request.url.path),
        'client_ip': request.client.host
    })
```

## Core API Endpoints

### 1. Root Endpoint
```http
GET /
```

**Response**:
```json
{
    "message": "Welcome to the LLM Powered Workload Monitoring API"
}
```

### 2. Workflow Management

#### Start New Workflow
```http
GET /start
```

**Purpose**: Initialize new monitoring workflow and begin workload detection

**Implementation**: 
- Creates new workflow thread with UUID
- Starts workload detection using K8sClient
- Runs OSS detection agent to identify monitoring candidates

**Response**:
```json
{
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "detected_oss_workloads": {
        "postgres-service": {
            "name": "postgres-service",
            "namespace": "production",
            "pretty_name": "postgresql",
            "service_type": "ClusterIP",
            "is_oss": true
        },
        "redis-service": {
            "name": "redis-service", 
            "namespace": "cache",
            "pretty_name": "redis",
            "service_type": "ClusterIP",
            "is_oss": true
        }
    }
}
```

**Error Responses**:
```json
// Kubernetes connection failure
{
    "detail": "Failed to connect to Kubernetes cluster",
    "error_code": "K8S_CONNECTION_ERROR"
}

// No workloads detected
{
    "detail": "No OSS workloads detected in cluster",
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "detected_oss_workloads": {}
}
```

#### Get Workflow Status
```http
GET /status/{thread_id}
```

**Path Parameters**:
- `thread_id` (string): Workflow thread identifier

**Response Model**: `WorkflowStatus`
```json
{
    "active": true,
    "thread_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "workload-selection",
    "config": {
        "configurable": {
            "thread_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    }
}
```

**Error Responses**:
```json
// Workflow not found
{
    "detail": "Workflow not found",
    "status_code": 404
}
```

### 3. Workload Selection

#### Select OSS Workloads
```http
POST /select_oss_workloads/{thread_id}
```

**Request Model**: `SelectOSSWorkloadsRequest`
```json
{
    "workload_keys": ["postgres-service", "redis-service"]
}
```

**Implementation**:
- Validates selected workloads exist in detected set
- Updates workflow state with selected workload
- Advances to monitoring plan generation phase

**Response**:
```json
{
    "message": "OSS workloads selected successfully",
    "selected_workloads": {
        "postgres-service": {
            "name": "postgres-service",
            "namespace": "production", 
            "pretty_name": "postgresql"
        }
    }
}
```

**Error Responses**:
```json
// Invalid workload selection
{
    "detail": "Selected workload not found in detected OSS workloads",
    "available_workloads": ["postgres-service", "redis-service"]
}

// Workflow not active
{
    "detail": "No active workflow found for this thread_id"
}
```

### 4. Monitoring Plan Generation

#### Generate Monitoring Plan
```http
POST /generate_monitoring_plan/{thread_id}
```

**Request Model**: `generateMonitoringPlanRequest`
```json
{
    "generate": true
}
```

**Implementation**:
- Uses LangGraph workflow resumption with `Command(resume=True)`
- Executes `generate_monitoring_deployment_plan` agent
- Generates markdown plan using GPT-5 model with tool integration

**Response**:
```json
{
    "message": "Monitoring deployment plan generated successfully",
    "monitoring_plan": {
        "markdown_plan": "# Monitoring Plan for PostgreSQL Service\n\n## Prerequisites\n...",
        "generation_timestamp": "2025-01-15T10:45:00Z"
    }
}
```

**Error Responses**:
```json
// Plan generation failure
{
    "detail": "Failed to generate monitoring plan",
    "error": "Agent response was empty or invalid"
}

// Workflow state error
{
    "detail": "Workflow not in correct phase for plan generation",
    "current_phase": "workload-selection",
    "required_phase": "monitoring-plan-generation"
}
```

### 5. Plan Evaluation

#### Evaluate Monitoring Plan
```http
POST /evaluate_monitoring_plan/{thread_id}
```

**Request Model**: `evaluateMonitoringPlanRequest`
```json
{
    "evaluate": true
}
```

**Implementation**:
- Runs critic agent with enhanced validation prompts
- Uses specialized tools for chart validation
- Supports multi-round evaluation with feedback

**Response**:
```json
{
    "message": "Monitoring plan evaluation completed", 
    "evaluation_feedback": {
        "critic_approved": true,
        "feedback_text": "Plan is comprehensive and follows Azure best practices",
        "round_count": 2
    }
}
```

**Error Responses**:
```json
// Evaluation failure
{
    "detail": "Plan evaluation failed",
    "error": "No monitoring plan found to evaluate"
}

// Max rounds reached
{
    "message": "Maximum evaluation rounds reached, plan auto-approved",
    "evaluation_feedback": {
        "critic_approved": true,
        "round_count": 3
    }
}
```

### 6. Plan Structure and Deployment

#### Get Structured Instructions
```http
POST /structure_monitoring_plan/{thread_id}
```

**Request Model**: `structureMonitoringPlanRequest`
```json
{
    "structure": true
}
```

**Implementation**:
- Converts markdown plan to structured instructions
- Creates typed instruction objects (Helm, Kubectl, CreateFile, Other)
- Validates instruction format and parameters

**Response**:
```json
{
    "message": "Monitoring plan structured successfully",
    "structured_plan": {
        "instructions": [
            {
                "type": "helm",
                "command": "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts"
            },
            {
                "type": "helm", 
                "command": "helm install postgres-exporter prometheus-community/prometheus-postgres-exporter --set serviceMonitor.enabled=true"
            },
            {
                "type": "kubectl",
                "command": "kubectl apply -f servicemonitor.yaml"
            }
        ]
    }
}
```

#### Deploy Monitoring Plan
```http
POST /deploy_monitoring_plan/{thread_id}
```

**Request Model**: `deployMonitoringPlanRequest`
```json
{
    "deploy": true
}
```

**Implementation**:
- Uses InstructionController for safe command execution
- Executes helm and kubectl commands in sequence
- Provides rollback capabilities on failure

**Response**:
```json
{
    "message": "Monitoring plan deployed successfully",
    "deployment_result": {
        "success": true,
        "executed_instructions": 5,
        "failed_instructions": 0
    }
}
```

**Error Responses**:
```json
// Deployment failure
{
    "detail": "Deployment failed",
    "error": "kubectl command failed: connection refused",
    "rollback_available": true
}

// Prerequisites not met
{
    "detail": "Prerequisites check failed",
    "missing_tools": ["kubectl", "helm"]
}
```

### 7. Dashboard and Alerting

#### Get Dashboard Recommendations
```http
POST /recommend_dashboards/{thread_id}
```

**Request Model**: `recommendDashboardsRequest`
```json
{
    "recommend": true
}
```

**Response**:
```json
{
    "message": "Dashboard recommendations generated",
    "recommended_dashboards": {
        "PostgreSQL Database": 9628,
        "PostgreSQL Overview": 455,
        "PostgreSQL Exporter Quickstart": 14114
    }
}
```

#### Get Alerting Rules Recommendations  
```http
POST /recommend_alerting_rules/{thread_id}
```

**Request Model**: `recommendAlertingRulesRequest`
```json
{
    "recommend": true
}
```

**Response**:
```json
{
    "message": "Alerting rules recommendations generated",
    "recommended_alerting_rules": {
        "rules_content": "groups:\n- name: postgresql\n  rules:\n  - alert: PostgreSQLDown\n    expr: pg_up == 0\n    for: 0m\n    labels:\n      severity: critical",
        "installation_instructions": "kubectl apply -f postgresql-alerts.yaml"
    }
}
```

## Error Handling

### Standard Error Response Format
```json
{
    "detail": "Error description",
    "error_code": "SPECIFIC_ERROR_CODE",
    "timestamp": "2025-01-15T10:30:00Z",
    "path": "/api/endpoint", 
    "thread_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Common HTTP Status Codes
- **200**: Success
- **400**: Bad Request (invalid parameters, workflow state issues)
- **404**: Not Found (workflow not found)
- **500**: Internal Server Error (system failures, agent errors)

### Error Categories

#### 1. Workflow State Errors
```json
{
    "detail": "Workflow not in correct phase",
    "error_code": "INVALID_WORKFLOW_PHASE",
    "current_phase": "workload-selection",
    "required_phase": "monitoring-plan-generation"
}
```

#### 2. Kubernetes Integration Errors
```json
{
    "detail": "Failed to connect to Kubernetes cluster",
    "error_code": "K8S_CONNECTION_ERROR",
    "kubeconfig_path": "/path/to/kubeconfig"
}
```

#### 3. AI Agent Errors
```json
{
    "detail": "Agent execution failed",
    "error_code": "AGENT_EXECUTION_ERROR", 
    "agent_type": "plan_generation",
    "error_details": "OpenAI API timeout"
}
```

## Middleware and Logging

### Request Logging Middleware
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests with meaningful system information."""
    start_time = time.time()
    
    logger.info("HTTP request received", extra={
        'component': 'api',
        'operation': 'request_start',
        'method': request.method,
        'path': str(request.url.path),
        'client_ip': request.client.host
    })
    
    response = await call_next(request)
    
    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info("HTTP request completed", extra={
        'method': request.method,
        'path': str(request.url.path),
        'status_code': response.status_code,
        'duration_ms': duration_ms
    })
    
    return response
```

## Workflow Management Implementation

### Async-Safe Workflow Storage
```python
# Global workflow storage with thread safety
_workflows: Dict[str, WorkflowStatus] = {}
_workflows_lock = asyncio.Lock()

# Graph instance management per workflow
_workflow_graphs: Dict[str, any] = {}
_graphs_lock = asyncio.Lock()

async def get_workflow_graph(thread_id: str):
    """Get or create a graph instance for specific workflow."""
    async with _graphs_lock:
        if thread_id not in _workflow_graphs:
            _workflow_graphs[thread_id] = await asyncio.to_thread(get_graph)
        return _workflow_graphs[thread_id]
```

### Graph Execution Pattern
```python
# Common pattern for executing workflow steps
async def execute_workflow_step(thread_id: str, command: Command):
    workflow_graph = await get_workflow_graph(thread_id)
    
    result = await asyncio.to_thread(
        workflow_graph.invoke,
        command,
        status.config
    )
    
    return result
```

## Integration Examples

### Python Client Integration
```python
import requests
import json

class MonitoringAutomationClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def start_workflow(self) -> dict:
        """Start new monitoring workflow."""
        response = requests.get(f"{self.base_url}/start")
        return response.json()
        
    def select_workloads(self, thread_id: str, workload_keys: list) -> dict:
        """Select OSS workloads for monitoring."""
        payload = {"workload_keys": workload_keys}
        response = requests.post(
            f"{self.base_url}/select_oss_workloads/{thread_id}",
            json=payload
        )
        return response.json()
        
    def generate_plan(self, thread_id: str) -> dict:
        """Generate monitoring deployment plan."""
        payload = {"generate": True}
        response = requests.post(
            f"{self.base_url}/generate_monitoring_plan/{thread_id}",
            json=payload
        )
        return response.json()

# Usage example
client = MonitoringAutomationClient()

# Start workflow
result = client.start_workflow()
thread_id = result["thread_id"]
workloads = result["detected_oss_workloads"]

# Select workloads
client.select_workloads(thread_id, list(workloads.keys())[:1])

# Generate plan
plan_result = client.generate_plan(thread_id)
print(plan_result["monitoring_plan"]["markdown_plan"])
```

### cURL Examples
```bash
# Start workflow
curl -X GET http://localhost:8000/start

# Check status
curl -X GET http://localhost:8000/status/{thread_id}

# Select workloads
curl -X POST http://localhost:8000/select_oss_workloads/{thread_id} \
  -H "Content-Type: application/json" \
  -d '{"workload_keys": ["postgres-service"]}'

# Generate plan
curl -X POST http://localhost:8000/generate_monitoring_plan/{thread_id} \
  -H "Content-Type: application/json" \
  -d '{"generate": true}'
```

## Security Considerations

### Input Validation
- All request models use Pydantic validation
- Thread ID format validation
- Workload key validation against detected workloads

### Command Execution Safety
- Commands are executed through InstructionController with validation
- Dry-run mode available for testing
- Command sanitization and shell injection prevention

### Error Information Disclosure
- Error messages designed to be informative but not expose sensitive data
- System errors logged separately from user-facing responses
- Kubernetes configuration details not exposed in API responses
