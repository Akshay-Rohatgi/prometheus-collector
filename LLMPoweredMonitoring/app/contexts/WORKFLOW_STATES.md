# Workflow State Management

## Overview

The LLM-Powered Monitoring System uses a sophisticated state machine implemented with LangGraph to orchestrate AI agents through a multi-phase monitoring setup workflow. This document provides comprehensive details about workflow states, transitions, and management.

## State Machine Architecture

### Core Components

1. **Workflow Class** (`core/workflow.py`)
   - Centralized state management
   - Phase tracking and validation
   - Configuration storage
   - Session lifecycle management

2. **LangGraph Integration** (`ai/graphs.py`)
   - State machine definition
   - Agent function routing
   - Interrupt handling
   - Conditional transitions

3. **State Storage** (`api/routes.py`)
   - Thread-safe workflow storage
   - Async-safe state management
   - Session persistence
   - Memory optimization

## Workflow Phases

### Phase 1: workload-detection

**Purpose**: Discover and classify OSS workloads in Kubernetes cluster

**State Structure**:
```python
{
    "phase": "workload-detection",
    "cluster_data": {
        "services": [...],          # Raw Kubernetes services
        "namespaces": [...],        # Available namespaces
        "nodes": [...],            # Cluster nodes info
        "metadata": {
            "cluster_version": "1.24.0",
            "total_services": 42,
            "scan_timestamp": "2025-09-05T10:30:00Z"
        }
    },
    "detected_workloads": {
        "workload_1": {
            "name": "postgres-service",
            "namespace": "production",
            "type": "postgresql",
            "confidence": 0.95,
            "endpoints": ["postgres-service.production.svc.cluster.local:5432"],
            "labels": {...},
            "annotations": {...}
        }
    }
}
```

**Agent Function**: `detect_workloads(workflow: Workflow) -> dict`

**Transitions**:
- **SUCCESS** → `workload-selection` (workloads found)
- **ERROR** → `error` (no workloads or connection issues)
- **RETRY** → `workload-detection` (transient failures)

**Exit Conditions**:
- Workloads successfully detected and classified
- No OSS workloads found (completion with empty result)
- Fatal error in Kubernetes connectivity

### Phase 2: workload-selection

**Purpose**: User selects which workloads to monitor

**State Structure**:
```python
{
    "phase": "workload-selection",
    "workload_options": {
        "postgresql_prod": "PostgreSQL Database (production)",
        "redis_cache": "Redis Cache (staging)",
        "nginx_ingress": "Nginx Ingress Controller"
    },
    "selected_workload": "postgresql_prod",  # User selection
    "selection_metadata": {
        "selection_timestamp": "2025-09-05T10:32:15Z",
        "available_count": 3,
        "selection_method": "interactive"
    }
}
```

**Interaction Type**: `interrupt` (requires user input)

**User Interface**:
```python
def select_oss_workloads(workflow: Workflow) -> dict:
    workload_keys = list(workflow.detected_workloads.keys())
    
    if len(workload_keys) == 0:
        return {"selected_workload": None}
    
    # Present options to user
    user_selection = interrupt({
        "message": "Select a workload to monitor:",
        "options": workload_keys,
        "type": "single_select",
        "required": True
    })
    
    return {"selected_workload": user_selection}
```

**Transitions**:
- **SELECTION_MADE** → `monitoring-plan-generation`
- **NO_SELECTION** → `completed` (user cancellation)
- **TIMEOUT** → `error` (no user response)

### Phase 3: monitoring-plan-generation

**Purpose**: AI agent generates monitoring configuration plan

**State Structure**:
```python
{
    "phase": "monitoring-plan-generation",
    "target_workload": {
        "name": "postgresql_prod",
        "details": {...}
    },
    "monitoring_plan": {
        "installation_commands": [
            "helm repo add prometheus-community https://...",
            "helm install postgres-exporter prometheus-community/prometheus-postgres-exporter ..."
        ],
        "configuration_files": {
            "values.yaml": "...",
            "servicemonitor.yaml": "...",
            "prometheusrule.yaml": "..."
        },
        "verification_commands": [
            "kubectl get servicemonitor postgres-exporter",
            "curl -s http://postgres-exporter:9187/metrics"
        ],
        "rollback_commands": [
            "helm uninstall postgres-exporter",
            "kubectl delete servicemonitor postgres-exporter"
        ],
        "metadata": {
            "plan_version": "1.0",
            "generated_timestamp": "2025-09-05T10:35:22Z",
            "chart_version": "4.2.1",
            "exporter_image": "prometheuscommunity/postgres_exporter:v0.11.1"
        }
    }
}
```

**Agent Function**: `generate_monitoring_deployment_plan(workflow: Workflow) -> dict`

**Tools Used**:
- **GitHub API**: Fetch Helm chart information
- **Azure OpenAI**: Generate configuration templates
- **Template Engine**: Customize deployment configurations

**Transitions**:
- **PLAN_GENERATED** → `monitoring-plan-evaluation`
- **GENERATION_FAILED** → `error`
- **RETRY_NEEDED** → `monitoring-plan-generation` (with retry count)

**Error Handling**:
```python
def handle_plan_generation_error(workflow: Workflow, error: Exception) -> dict:
    retry_count = workflow.config.get("plan_generation_retries", 0)
    max_retries = 3
    
    if retry_count < max_retries:
        return {
            "phase": "monitoring-plan-generation",
            "config": {
                **workflow.config,
                "plan_generation_retries": retry_count + 1,
                "last_error": str(error)
            }
        }
    else:
        return {
            "phase": "error",
            "error": f"Plan generation failed after {max_retries} attempts: {error}"
        }
```

### Phase 4: monitoring-plan-evaluation

**Purpose**: AI critic agent evaluates and improves the monitoring plan

**State Structure**:
```python
{
    "phase": "monitoring-plan-evaluation",
    "current_plan": {...},          # Plan under evaluation
    "evaluation_history": [
        {
            "round": 1,
            "timestamp": "2025-09-05T10:36:00Z",
            "evaluation": {
                "approved": False,
                "feedback": "Missing alert rules for connection failures",
                "suggestions": [
                    "Add PrometheusRule for connection monitoring",
                    "Include disk space alerts",
                    "Add service discovery labels"
                ],
                "score": 7.5
            }
        }
    ],
    "monitoring_plan_feedback": {
        "critic_approved": True,
        "feedback_text": "Plan is comprehensive and production-ready",
        "round_count": 2,
        "final_score": 9.2,
        "approval_timestamp": "2025-09-05T10:38:45Z"
    }
}
```

**Agent Function**: `evaluate_monitoring_deployment_plan(workflow: Workflow) -> dict`

**Evaluation Criteria**:
- Configuration completeness and accuracy
- Security best practices
- Performance considerations
- Operational maintainability
- Azure AKS compatibility

**Iterative Improvement**:
```python
def evaluate_plan_iteratively(workflow: Workflow) -> dict:
    max_rounds = 3
    current_round = len(workflow.evaluation_history) + 1
    
    if current_round > max_rounds:
        # Auto-approve after max iterations
        return {
            "monitoring_plan_feedback": MonitoringFeedback(
                critic_approved=True,
                feedback_text=f"Auto-approved after {max_rounds} evaluation rounds",
                round_count=current_round
            )
        }
    
    # Perform evaluation
    evaluation_result = critic_agent.evaluate(workflow.monitoring_plan)
    
    if evaluation_result.approved:
        return {
            "monitoring_plan_feedback": MonitoringFeedback(
                critic_approved=True,
                feedback_text=evaluation_result.feedback,
                round_count=current_round
            )
        }
    else:
        # Generate improved plan
        improved_plan = generate_improved_plan(
            workflow.monitoring_plan,
            evaluation_result.feedback
        )
        
        return {
            "monitoring_plan": improved_plan,
            "evaluation_history": workflow.evaluation_history + [evaluation_result],
            "phase": "monitoring-plan-generation"  # Return to generation
        }
```

**Transitions**:
- **APPROVED** → `deployment-execution`
- **NEEDS_IMPROVEMENT** → `monitoring-plan-generation` (with feedback)
- **MAX_ITERATIONS_REACHED** → `deployment-execution` (auto-approve)

### Phase 5: deployment-execution

**Purpose**: Execute the approved monitoring plan

**State Structure**:
```python
{
    "phase": "deployment-execution",
    "approved_plan": {...},          # Final approved plan
    "execution_log": [
        {
            "command": "helm repo add prometheus-community https://...",
            "timestamp": "2025-09-05T10:40:12Z",
            "status": "success",
            "output": "prometheus-community has been added to your repositories",
            "duration_ms": 1250
        },
        {
            "command": "helm install postgres-exporter ...",
            "timestamp": "2025-09-05T10:40:15Z",
            "status": "success",
            "output": "NAME: postgres-exporter\nLAST DEPLOYED: ...",
            "duration_ms": 5400
        }
    ],
    "deployment_status": {
        "status": "completed",
        "success": True,
        "completion_timestamp": "2025-09-05T10:42:30Z",
        "total_duration_ms": 138000,
        "deployed_components": [
            "postgres-exporter-deployment",
            "postgres-exporter-service",
            "postgres-exporter-servicemonitor"
        ]
    }
}
```

**Agent Function**: `execute_deployment_plan(workflow: Workflow) -> dict`

**Execution Process**:
1. **Preparation**: Validate cluster connectivity and permissions
2. **Repository Setup**: Add Helm repositories
3. **Deployment**: Install monitoring components
4. **Verification**: Confirm successful deployment
5. **Configuration**: Apply additional configurations
6. **Validation**: Test metrics collection

**Error Handling and Rollback**:
```python
def execute_with_rollback(workflow: Workflow) -> dict:
    deployment_steps = workflow.approved_plan.installation_commands
    executed_steps = []
    
    try:
        for step in deployment_steps:
            result = execute_command(step)
            executed_steps.append({
                "command": step,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            if result.return_code != 0:
                raise DeploymentError(f"Command failed: {step}")
        
        return {
            "deployment_status": {
                "status": "completed",
                "success": True,
                "execution_log": executed_steps
            },
            "phase": "completed"
        }
        
    except Exception as e:
        # Execute rollback
        rollback_commands = workflow.approved_plan.rollback_commands
        for rollback_cmd in reversed(rollback_commands):
            try:
                execute_command(rollback_cmd)
            except Exception as rollback_error:
                logger.error(f"Rollback command failed: {rollback_error}")
        
        return {
            "deployment_status": {
                "status": "failed",
                "success": False,
                "error": str(e),
                "execution_log": executed_steps
            },
            "phase": "error"
        }
```

**Transitions**:
- **SUCCESS** → `completed`
- **FAILURE** → `error` (with rollback)
- **PARTIAL_SUCCESS** → `manual-intervention-required`

### Phase 6: completed

**Purpose**: Workflow completion and cleanup

**State Structure**:
```python
{
    "phase": "completed",
    "completion_summary": {
        "success": True,
        "start_time": "2025-09-05T10:30:00Z",
        "end_time": "2025-09-05T10:42:30Z",
        "total_duration_ms": 750000,
        "workload_monitored": "postgresql_prod",
        "components_deployed": 3,
        "metrics_endpoints": [
            "http://postgres-exporter.production.svc.cluster.local:9187/metrics"
        ]
    },
    "next_steps": [
        "Configure Grafana dashboards",
        "Set up alerting rules",
        "Review metric collection after 24 hours"
    ],
    "monitoring_urls": {
        "prometheus_targets": "http://prometheus.monitoring.svc.cluster.local:9090/targets",
        "grafana_dashboards": "http://grafana.monitoring.svc.cluster.local:3000"
    }
}
```

**Cleanup Actions**:
- Release workflow resources
- Archive execution logs
- Send completion notifications
- Update monitoring inventory

### Error Phase: error

**Purpose**: Handle workflow failures and provide recovery options

**State Structure**:
```python
{
    "phase": "error",
    "error_details": {
        "error_type": "KubernetesConnectionError",
        "error_message": "Failed to connect to cluster",
        "error_timestamp": "2025-09-05T10:33:22Z",
        "source_phase": "workload-detection",
        "stack_trace": "...",
        "recovery_suggestions": [
            "Check cluster connectivity",
            "Verify RBAC permissions",
            "Restart workflow from workload-detection"
        ]
    },
    "recovery_options": {
        "retry_from_beginning": True,
        "retry_from_failed_phase": True,
        "manual_intervention": False
    }
}
```

## State Transitions

### Transition Logic

```python
def route_workflow(workflow: Workflow) -> str:
    """Determine next workflow phase based on current state."""
    
    current_phase = workflow.phase
    
    if current_phase == "workload-detection":
        if workflow.detected_workloads:
            return "workload-selection"
        else:
            return "completed"  # No workloads found
    
    elif current_phase == "workload-selection":
        if workflow.selected_workload:
            return "monitoring-plan-generation"
        else:
            return "completed"  # User cancellation
    
    elif current_phase == "monitoring-plan-generation":
        if workflow.monitoring_plan:
            return "monitoring-plan-evaluation"
        else:
            return "error"  # Plan generation failed
    
    elif current_phase == "monitoring-plan-evaluation":
        if workflow.monitoring_plan_feedback.critic_approved:
            return "deployment-execution"
        else:
            # Return to plan generation with feedback
            return "monitoring-plan-generation"
    
    elif current_phase == "deployment-execution":
        if workflow.deployment_status.success:
            return "completed"
        else:
            return "error"
    
    elif current_phase in ["completed", "error"]:
        return "__end__"  # Terminal states
    
    else:
        return "error"  # Unknown phase
```

### Conditional Routing

```python
def create_workflow_graph():
    """Create LangGraph workflow with conditional routing."""
    
    workflow = StateGraph(Workflow)
    
    # Add nodes for each phase
    workflow.add_node("workload-detection", detect_workloads)
    workflow.add_node("workload-selection", select_oss_workloads)
    workflow.add_node("monitoring-plan-generation", generate_monitoring_deployment_plan)
    workflow.add_node("monitoring-plan-evaluation", evaluate_monitoring_deployment_plan)
    workflow.add_node("deployment-execution", execute_deployment_plan)
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "workload-detection",
        route_workflow,
        {
            "workload-selection": "workload-selection",
            "completed": "__end__",
            "error": "__end__"
        }
    )
    
    workflow.add_conditional_edges(
        "workload-selection",
        route_workflow,
        {
            "monitoring-plan-generation": "monitoring-plan-generation",
            "completed": "__end__"
        }
    )
    
    # Set entry point
    workflow.set_entry_point("workload-detection")
    
    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["workload-selection"]  # User interaction points
    )
```

## Interrupt Handling

### User Interaction Points

The workflow includes strategic interrupt points where user input is required:

```python
def select_oss_workloads(workflow: Workflow) -> dict:
    """Handle workload selection with user interrupt."""
    
    workload_options = {
        key: f"{workload.name} ({workload.type})"
        for key, workload in workflow.detected_workloads.items()
    }
    
    if not workload_options:
        return {"selected_workload": None}
    
    # Trigger interrupt for user selection
    user_choice = interrupt({
        "type": "workload_selection",
        "message": "Select a workload to monitor:",
        "options": workload_options,
        "required": True,
        "timeout": 300  # 5 minutes
    })
    
    return {"selected_workload": user_choice}
```

### Resume Handling

```python
async def resume_workflow(thread_id: str, user_input: Any):
    """Resume workflow after user interaction."""
    
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Resume with user input
    result = await graph.ainvoke(
        Command(resume=value=user_input),
        config=config
    )
    
    return result
```

## State Persistence

### Memory Management

```python
# api/routes.py
_workflows: Dict[str, Workflow] = {}
_workflows_lock = asyncio.Lock()

async def store_workflow(thread_id: str, workflow: Workflow):
    """Store workflow state with thread safety."""
    
    async with _workflows_lock:
        _workflows[thread_id] = workflow
        
        # Memory cleanup for completed workflows
        if workflow.phase in ["completed", "error"]:
            # Schedule cleanup after delay
            asyncio.create_task(cleanup_workflow(thread_id, delay=3600))

async def cleanup_workflow(thread_id: str, delay: int):
    """Clean up completed workflow after delay."""
    
    await asyncio.sleep(delay)
    
    async with _workflows_lock:
        if thread_id in _workflows:
            workflow = _workflows[thread_id]
            if workflow.phase in ["completed", "error"]:
                del _workflows[thread_id]
                logger.info(f"Cleaned up workflow {thread_id}")
```

### Checkpointing

```python
from langgraph.checkpoint import MemorySaver

# Create checkpointer for state persistence
checkpointer = MemorySaver()

# Compile graph with checkpointing
graph = workflow.compile(
    checkpointer=checkpointer,
    interrupt_before=["workload-selection"]
)
```

## Error Recovery

### Retry Mechanisms

```python
def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for automatic retry with exponential backoff."""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(workflow: Workflow) -> dict:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(workflow)
                except RetryableError as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (2 ** attempt)
                        await asyncio.sleep(wait_time)
                        logger.warning(f"Retry attempt {attempt + 1} for {func.__name__}")
                except Exception as e:
                    # Non-retryable error
                    raise e
            
            # All retries exhausted
            raise last_exception
        
        return wrapper
    return decorator

# Usage
@with_retry(max_attempts=3, delay=2.0)
async def detect_workloads(workflow: Workflow) -> dict:
    # Workload detection logic with automatic retry
    pass
```

### Graceful Degradation

```python
def handle_partial_failure(workflow: Workflow, error: Exception) -> dict:
    """Handle partial failures with graceful degradation."""
    
    if isinstance(error, KubernetesTimeoutError):
        # Reduce scope and retry
        return {
            "config": {
                **workflow.config,
                "reduced_scope": True,
                "timeout": workflow.config.get("timeout", 30) * 2
            },
            "phase": workflow.phase  # Retry same phase
        }
    
    elif isinstance(error, PermissionError):
        # Suggest manual intervention
        return {
            "phase": "manual-intervention-required",
            "intervention_details": {
                "required_permissions": ["list services", "create servicemonitors"],
                "suggested_actions": ["Update RBAC configuration", "Contact cluster admin"]
            }
        }
    
    else:
        # Unrecoverable error
        return {
            "phase": "error",
            "error_details": {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "recovery_possible": False
            }
        }
```

This comprehensive workflow state management system ensures reliable, traceable, and recoverable execution of the monitoring setup process while providing clear user interaction points and robust error handling.
