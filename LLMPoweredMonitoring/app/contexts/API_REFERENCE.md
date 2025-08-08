# API Reference and Integration Guide

## Overview

The system exposes a RESTful API built with FastAPI for workflow management and monitoring automation. This document provides comprehensive API documentation and integration examples.

## Base Configuration

### Server Setup
```python
# FastAPI application configuration
app = FastAPI(
    title="LLM-Powered Monitoring System",
    description="Automated Kubernetes monitoring deployment with AI agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for web UI integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Base URL Structure
```
Production:  https://monitoring-automation.your-domain.com/api/v1
Development: http://localhost:8000/api/v1
Local:       http://127.0.0.1:8000/api/v1
```

## Core API Endpoints

### 1. Workflow Management

#### Create New Workflow Session
```http
POST /api/v1/workflow
Content-Type: application/json

{
    "cluster_config": {
        "kubeconfig_path": "/path/to/kubeconfig",
        "context": "production-cluster"
    },
    "options": {
        "auto_approve": false,
        "dry_run": false,
        "namespace_filter": "production,staging"
    }
}
```

**Response**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "created",
    "phase": "workload-detection",
    "timestamp": "2025-01-15T10:30:00Z",
    "next_action": "Start workload detection process"
}
```

#### Get Workflow Status
```http
GET /api/v1/workflow/{session_id}
```

**Response**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "workload-selection",
    "status": "waiting_for_input",
    "progress": {
        "completed_phases": ["workload-detection"],
        "current_phase": "workload-selection", 
        "total_phases": 6,
        "percentage": 17
    },
    "data": {
        "detected_workloads": [
            {
                "name": "postgres-service",
                "namespace": "production",
                "type": "postgresql",
                "monitoring_potential": "high"
            }
        ]
    },
    "timestamp": "2025-01-15T10:35:22Z"
}
```

#### Advance Workflow Phase
```http
POST /api/v1/workflow/{session_id}/advance
Content-Type: application/json

{
    "input_data": {
        "selected_workloads": [
            {
                "name": "postgres-service",
                "namespace": "production",
                "confirmed": true
            }
        ]
    }
}
```

**Response**:
```json
{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "previous_phase": "workload-selection",
    "current_phase": "monitoring-plan-generation",
    "status": "processing",
    "estimated_completion": "2025-01-15T10:42:00Z"
}
```

### 2. Workload Discovery

#### List Detected Workloads
```http
GET /api/v1/workflow/{session_id}/workloads
```

**Response**:
```json
{
    "total_services": 45,
    "filtered_services": 8,
    "detected_workloads": [
        {
            "service_name": "postgres-primary",
            "namespace": "production",
            "oss_type": "postgresql", 
            "monitoring_potential": "high",
            "current_monitoring": "none",
            "recommended_approach": "ServiceMonitor + exporter sidecar",
            "estimated_metrics_volume": "~500 series",
            "ports": [
                {"name": "postgres", "port": 5432},
                {"name": "metrics", "port": 9187}
            ],
            "labels": {
                "app.kubernetes.io/name": "postgresql",
                "app.kubernetes.io/version": "13.8"
            }
        }
    ],
    "filtering_stats": {
        "total_discovered": 45,
        "system_services_filtered": 25,
        "non_oss_filtered": 12,
        "monitoring_candidates": 8
    }
}
```

#### Get Workload Details
```http
GET /api/v1/workload/{namespace}/{service_name}
```

**Response**:
```json
{
    "service_name": "postgres-primary",
    "namespace": "production",
    "detailed_analysis": {
        "oss_classification": {
            "type": "postgresql",
            "confidence": 0.95,
            "detection_method": ["image_analysis", "port_pattern", "labels"]
        },
        "monitoring_assessment": {
            "current_state": "no_monitoring",
            "monitoring_potential": "high",
            "available_exporters": ["postgres_exporter", "pg_stat_statements"],
            "metric_endpoints": ["/metrics"]
        },
        "resource_analysis": {
            "replicas": 2,
            "resource_requests": {"cpu": "500m", "memory": "1Gi"},
            "storage": "100Gi",
            "high_availability": true
        },
        "related_resources": {
            "deployments": ["postgres-primary"],
            "statefulsets": [],
            "configmaps": ["postgres-config", "postgres-init"],
            "secrets": ["postgres-credentials"]
        }
    }
}
```

### 3. Monitoring Plans

#### Get Generated Plan
```http
GET /api/v1/workflow/{session_id}/plan
```

**Response**:
```json
{
    "plan_id": "plan_550e8400_v1", 
    "generation_timestamp": "2025-01-15T10:38:15Z",
    "plan_format": "markdown",
    "plan_content": "# Monitoring Plan for PostgreSQL Service\n\n## Overview\nThis plan establishes comprehensive monitoring...",
    "structured_preview": {
        "components": ["ServiceMonitor", "PrometheusRule", "Grafana Dashboard"],
        "estimated_resources": {
            "cpu": "200m",
            "memory": "512Mi",
            "storage": "10Gi"
        },
        "monitoring_coverage": {
            "availability": true,
            "performance": true,
            "errors": true,
            "capacity": true
        }
    },
    "evaluation_status": "pending"
}
```

#### Request Plan Evaluation
```http
POST /api/v1/workflow/{session_id}/evaluate-plan
```

**Response**:
```json
{
    "evaluation_id": "eval_550e8400_v1",
    "status": "evaluating",
    "estimated_completion": "2025-01-15T10:45:00Z",
    "evaluation_criteria": [
        "technical_accuracy",
        "completeness", 
        "best_practices",
        "azure_compatibility"
    ]
}
```

#### Get Plan Evaluation Results
```http
GET /api/v1/workflow/{session_id}/evaluation
```

**Response**:
```json
{
    "evaluation_id": "eval_550e8400_v1",
    "overall_score": 8.5,
    "detailed_scores": {
        "technical_accuracy": 9.0,
        "completeness": 8.0,
        "best_practices": 8.5,
        "azure_compatibility": 9.0
    },
    "feedback": {
        "strengths": [
            "Comprehensive metric coverage for PostgreSQL",
            "Proper ServiceMonitor configuration",
            "Well-structured alerting rules"
        ],
        "improvements": [
            "Add capacity planning alerts for storage",
            "Include connection pool monitoring",
            "Consider query performance metrics"
        ],
        "critical_issues": []
    },
    "revised_plan": "# Improved Monitoring Plan...",
    "recommendation": "approve_with_minor_changes"
}
```

### 4. Deployment Management

#### Get Structured Instructions
```http
GET /api/v1/workflow/{session_id}/instructions
```

**Response**:
```json
{
    "instruction_set_id": "inst_550e8400_v1",
    "total_instructions": 5,
    "estimated_duration": "3-5 minutes",
    "prerequisites": [
        {
            "type": "permission",
            "resource": "monitoring.coreos.com/servicemonitors",
            "action": "create"
        },
        {
            "type": "helm_repository",
            "repository": "prometheus-community",
            "url": "https://prometheus-community.github.io/helm-charts"
        }
    ],
    "instructions": [
        {
            "order": 1,
            "type": "helm",
            "action": "repo_add",
            "repository": "prometheus-community",
            "url": "https://prometheus-community.github.io/helm-charts"
        },
        {
            "order": 2,
            "type": "helm",
            "action": "install",
            "release_name": "postgres-monitoring",
            "chart": "prometheus-community/prometheus-postgres-exporter",
            "namespace": "production",
            "values": {
                "serviceMonitor": {"enabled": true},
                "datasource": {
                    "host": "postgres-primary",
                    "user": "monitoring",
                    "passwordSecret": {
                        "name": "postgres-monitoring-secret",
                        "key": "password"
                    }
                }
            }
        }
    ]
}
```

#### Execute Deployment
```http
POST /api/v1/workflow/{session_id}/deploy
Content-Type: application/json

{
    "confirmation": true,
    "options": {
        "dry_run": false,
        "timeout": 600,
        "wait_for_ready": true
    }
}
```

**Response**:
```json
{
    "deployment_id": "deploy_550e8400_v1",
    "status": "executing",
    "progress": {
        "completed_instructions": 1,
        "total_instructions": 5,
        "current_instruction": "Installing postgres-exporter Helm chart",
        "percentage": 20
    },
    "estimated_completion": "2025-01-15T10:55:00Z"
}
```

#### Get Deployment Status
```http
GET /api/v1/deployment/{deployment_id}/status
```

**Response**:
```json
{
    "deployment_id": "deploy_550e8400_v1",
    "status": "completed",
    "completion_time": "2025-01-15T10:52:30Z",
    "results": [
        {
            "instruction_order": 1,
            "type": "helm",
            "action": "repo_add",
            "status": "success",
            "duration": "2.3s",
            "output": "\"prometheus-community\" has been added to your repositories"
        },
        {
            "instruction_order": 2,
            "type": "helm", 
            "action": "install",
            "status": "success",
            "duration": "45.2s",
            "output": "Release \"postgres-monitoring\" deployed successfully"
        }
    ],
    "deployed_resources": [
        {
            "type": "ServiceMonitor",
            "name": "postgres-primary-monitor",
            "namespace": "production"
        },
        {
            "type": "Deployment",
            "name": "postgres-exporter",
            "namespace": "production"
        }
    ],
    "verification": {
        "metrics_available": true,
        "scrape_targets_healthy": true,
        "dashboard_accessible": true
    }
}
```

### 5. Dashboard Recommendations

#### Get Dashboard Recommendations
```http
GET /api/v1/workflow/{session_id}/dashboards
```

**Response**:
```json
{
    "recommended_dashboards": [
        {
            "dashboard_id": "9628",
            "name": "PostgreSQL Database",
            "description": "Comprehensive PostgreSQL monitoring with performance metrics",
            "url": "https://grafana.com/grafana/dashboards/9628",
            "rating": 4.8,
            "downloads": 125000,
            "last_updated": "2024-12-15T00:00:00Z",
            "compatibility": {
                "prometheus_version": ">=2.30",
                "grafana_version": ">=8.0",
                "azure_managed_prometheus": true
            },
            "import_method": "dashboard_id",
            "required_datasource": "Prometheus",
            "preview_image": "https://grafana.com/api/dashboards/9628/images/6418/image",
            "panels": [
                "Database Overview",
                "Query Performance", 
                "Connection Statistics",
                "Replication Status"
            ],
            "tags": ["postgresql", "database", "performance", "monitoring"]
        }
    ],
    "import_instructions": {
        "grafana_ui": "Grafana → + → Import → Dashboard ID: 9628",
        "api_endpoint": "/api/v1/dashboard/import",
        "terraform": "grafana_dashboard resource with dashboard_id"
    }
}
```

## Error Handling

### Standard Error Response Format
```json
{
    "error": {
        "code": "WORKFLOW_NOT_FOUND",
        "message": "Workflow session not found",
        "details": {
            "session_id": "invalid-session-id",
            "available_sessions": ["550e8400-e29b-41d4-a716-446655440000"]
        },
        "timestamp": "2025-01-15T10:30:00Z",
        "request_id": "req_12345"
    }
}
```

### Error Codes

#### Client Errors (4xx)
- `INVALID_INPUT` - Malformed request data
- `WORKFLOW_NOT_FOUND` - Session ID does not exist
- `INVALID_PHASE` - Cannot perform action in current workflow phase
- `MISSING_PERMISSION` - Insufficient Kubernetes permissions
- `VALIDATION_ERROR` - Input data failed validation

#### Server Errors (5xx)  
- `AI_AGENT_ERROR` - LLM agent execution failed
- `KUBERNETES_ERROR` - Cluster connectivity or API error
- `DEPLOYMENT_ERROR` - Infrastructure deployment failed
- `INTERNAL_ERROR` - Unexpected system error

## Authentication & Authorization

### API Key Authentication
```http
Authorization: Bearer your-api-key-here
```

### Kubernetes Authentication
The system uses the configured Kubernetes credentials for cluster access. Ensure proper RBAC permissions are configured.

### Rate Limiting
- **General API**: 100 requests per minute per IP
- **Workflow operations**: 10 requests per minute per session
- **Deployment operations**: 5 requests per minute per session

## SDK and Client Libraries

### Python Client Example
```python
import asyncio
from monitoring_client import MonitoringClient

async def setup_monitoring():
    client = MonitoringClient(
        base_url="https://monitoring-automation.your-domain.com/api/v1",
        api_key="your-api-key"
    )
    
    # Create workflow
    session = await client.create_workflow({
        "cluster_config": {"kubeconfig_path": "~/.kube/config"}
    })
    
    # Wait for workload detection
    await client.wait_for_phase(session.id, "workload-selection")
    
    # Get detected workloads
    workloads = await client.get_workloads(session.id)
    
    # Select workloads for monitoring
    selected = [w for w in workloads if w.monitoring_potential == "high"]
    await client.advance_workflow(session.id, {"selected_workloads": selected})
    
    # Continue through workflow...
    await client.wait_for_completion(session.id)
    
    print(f"Monitoring setup completed for session {session.id}")

# Run the workflow
asyncio.run(setup_monitoring())
```

### JavaScript/TypeScript Client
```typescript
import { MonitoringClient } from '@your-org/monitoring-client';

const client = new MonitoringClient({
  baseUrl: 'https://monitoring-automation.your-domain.com/api/v1',
  apiKey: 'your-api-key'
});

async function setupMonitoring() {
  // Create and manage workflow
  const session = await client.createWorkflow({
    cluster_config: { kubeconfig_path: '~/.kube/config' }
  });
  
  // Monitor progress
  const status = await client.getWorkflowStatus(session.session_id);
  console.log(`Current phase: ${status.phase}`);
  
  // Handle workload selection
  if (status.phase === 'workload-selection') {
    const workloads = status.data.detected_workloads;
    const selected = workloads.filter(w => w.monitoring_potential === 'high');
    
    await client.advanceWorkflow(session.session_id, {
      selected_workloads: selected
    });
  }
}
```

## Webhook Integration

### Workflow Progress Webhooks
Configure webhooks to receive real-time workflow updates:

```http
POST /api/v1/webhook/configure
Content-Type: application/json

{
    "webhook_url": "https://your-system.com/monitoring-webhook",
    "events": ["workflow.phase_change", "deployment.completed", "error.occurred"],
    "secret": "your-webhook-secret",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Webhook Payload Example
```json
{
    "event": "workflow.phase_change",
    "timestamp": "2025-01-15T10:42:00Z",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "data": {
        "previous_phase": "monitoring-plan-generation",
        "current_phase": "monitoring-plan-evaluation",
        "progress_percentage": 50,
        "estimated_completion": "2025-01-15T10:45:00Z"
    }
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- **Interactive docs**: `/docs` (Swagger UI)
- **ReDoc**: `/redoc` (ReDoc interface)
- **JSON spec**: `/openapi.json`
- **YAML spec**: `/openapi.yaml`
