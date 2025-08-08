# AI Agents and LLM Integration Guide

## Agent Architecture Overview

The system employs specialized AI agents, each with distinct responsibilities and prompt engineering optimizations. All agents are built on top of LangChain/LangGraph with structured output parsing.

## Core Agent Types

### 1. Workload Detection Agent
**File**: `ai/graphs.py` - `workload_detection_node()`
**Purpose**: Analyze Kubernetes services and identify OSS components suitable for monitoring

#### Prompt Strategy
```
System Role: Expert Kubernetes administrator and monitoring specialist
Task: Analyze cluster services and identify open-source software worth monitoring
Focus Areas:
- Databases (PostgreSQL, MySQL, Redis, MongoDB)
- Message queues (RabbitMQ, Kafka, NATS)
- Web servers (Nginx, Apache)
- Application frameworks
- Exclude: System services, operators, monitoring itself
```

#### Input Processing
- Raw Kubernetes service discovery data
- Service annotations and labels
- Container image analysis
- Port and protocol inspection

#### Output Structure
```python
[{
    "service_name": "postgres-service",
    "namespace": "production", 
    "oss_type": "postgresql",
    "monitoring_potential": "high",
    "reasoning": "Database service with standard PostgreSQL metrics",
    "recommended_approach": "ServiceMonitor + Grafana dashboard"
}]
```

### 2. Monitoring Plan Generator
**File**: `ai/graphs.py` - `monitoring_plan_generation_node()`
**Purpose**: Create comprehensive monitoring deployment plans

#### Prompt Engineering
```
System Role: Senior DevOps engineer specializing in Prometheus monitoring
Context: Azure Managed Prometheus environment
Requirements:
- Generate complete monitoring stack deployment
- Include ServiceMonitor configurations
- Specify AlertManager rules
- Reference production-ready Helm charts
- Consider resource requirements and scaling
```

#### Tool Integration
- **helm_search_tool**: Find appropriate monitoring charts
- **kubernetes_api_tool**: Validate cluster capabilities
- **prometheus_config_tool**: Generate ServiceMonitor configs

#### Plan Structure (Markdown)
```markdown
# Monitoring Plan for [Workload Name]

## Overview
[High-level monitoring strategy]

## Components
### 1. Metrics Collection
- ServiceMonitor configuration
- Prometheus scrape configs
- Custom metric endpoints

### 2. Alerting Rules
- Critical alerts (downtime, errors)
- Warning alerts (performance, capacity)
- Alert routing and notification

### 3. Dashboards
- Primary operational dashboard
- Detailed performance metrics
- Capacity planning views

## Implementation Steps
1. Deploy monitoring stack
2. Configure service discovery
3. Import dashboards
4. Test alert delivery
```

### 3. Plan Evaluator (Critic Agent)
**File**: `ai/graphs.py` - `monitoring_plan_evaluation_node()`
**Purpose**: Review and improve monitoring plans with expert critique

#### Evaluation Criteria
```
Technical Accuracy:
- Correct Prometheus configuration syntax
- Valid Kubernetes resource definitions
- Appropriate metric selection

Completeness:
- Coverage of critical failure modes
- Balanced alert thresholds
- Proper dashboard organization

Best Practices:
- Resource efficiency
- Security considerations
- Maintainability

Azure Integration:
- Azure Managed Prometheus compatibility
- Proper service discovery
- Workload identity usage
```

#### Feedback Format
```python
{
    "overall_score": 8.5,
    "technical_accuracy": 9.0,
    "completeness": 8.0,
    "best_practices": 8.5,
    "feedback": {
        "strengths": ["Comprehensive metric coverage", "Well-structured alerts"],
        "improvements": ["Add capacity planning alerts", "Optimize scrape intervals"],
        "critical_issues": []
    },
    "revised_plan": "improved_markdown_plan"
}
```

### 4. Dashboard Recommender
**File**: `ai/graphs.py` - `dashboard_recommendation_node()`
**Purpose**: Suggest relevant Grafana dashboards based on deployed monitoring

#### Recommendation Logic
```
Analysis Process:
1. Identify deployed monitoring components
2. Match against Grafana.com dashboard library
3. Prioritize by:
   - Community adoption (download count)
   - Maintenance status (recent updates)
   - Compatibility with metric names
   - Visual quality and completeness

Selection Criteria:
- Official vendor dashboards (preferred)
- High community rating (>4.0 stars)
- Active maintenance (updated <6 months)
- Compatible with Azure Managed Prometheus
```

#### Output Format
```python
[{
    "dashboard_id": "9628",
    "name": "PostgreSQL Database",
    "description": "Comprehensive PostgreSQL monitoring with query performance",
    "url": "https://grafana.com/grafana/dashboards/9628",
    "rating": 4.8,
    "downloads": 125000,
    "last_updated": "2024-12-15",
    "compatibility": "verified",
    "import_method": "dashboard_id",
    "required_datasource": "Prometheus",
    "tags": ["postgresql", "database", "performance"]
}]
```

## LLM Configuration

### Model Selection Strategy
```python
# Primary models by task complexity
TASK_MODEL_MAPPING = {
    "workload_detection": "gpt-4o-mini",     # Fast, cost-effective
    "plan_generation": "gpt-4",              # High-quality planning
    "plan_evaluation": "gpt-4",              # Critical analysis
    "dashboard_recommendation": "gpt-4o-mini" # Pattern matching
}

# Fallback chain
FALLBACK_MODELS = ["gpt-4", "gpt-4o-mini", "gpt-3.5-turbo"]
```

### Token Management
```python
# Estimated token usage per agent
AGENT_TOKEN_ESTIMATES = {
    "workload_detection": {
        "input": 2000,   # Cluster data + prompt
        "output": 800    # Service list + reasoning
    },
    "plan_generation": {
        "input": 3500,   # Context + requirements + examples
        "output": 2000   # Detailed plan
    },
    "plan_evaluation": {
        "input": 4000,   # Plan + evaluation criteria
        "output": 1500   # Critique + improvements
    }
}
```

### Prompt Templates

#### Base System Prompt
```python
SYSTEM_PROMPT_BASE = """
You are an expert DevOps engineer specializing in Kubernetes monitoring with Prometheus and Grafana.

Context:
- Target Environment: Azure Managed Prometheus
- Kubernetes Distribution: AKS (Azure Kubernetes Service)
- Monitoring Stack: Prometheus + Grafana + AlertManager
- Focus: Production-ready, scalable monitoring solutions

Guidelines:
- Prioritize reliability over complexity
- Use industry best practices
- Consider resource efficiency
- Ensure security compliance
- Provide clear, actionable recommendations

Output Format: {format_instructions}
"""
```

#### Tool Integration Prompts
```python
TOOL_USAGE_PROMPT = """
Available Tools:
- helm_search: Find Helm charts for monitoring components
- k8s_query: Query Kubernetes API for cluster information
- prometheus_validate: Validate Prometheus configuration syntax

When using tools:
1. Always validate configurations before recommending
2. Prefer official/community-maintained charts
3. Check compatibility with target Kubernetes version
4. Consider resource requirements and limits
"""
```

## Error Handling and Retry Logic

### Agent Failure Recovery
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(LLMException)
)
async def execute_agent(agent_name: str, input_data: dict):
    try:
        result = await agent.invoke(input_data)
        return validate_agent_output(result)
    except ValidationError as e:
        # Try with different model
        fallback_result = await execute_with_fallback_model(agent_name, input_data)
        return fallback_result
    except RateLimitError:
        # Exponential backoff handled by decorator
        raise
```

### Output Validation
```python
def validate_agent_output(output: dict, expected_schema: dict) -> dict:
    """Validate agent output against expected schema"""
    try:
        # JSON schema validation
        validate(instance=output, schema=expected_schema)
        
        # Business logic validation
        if output.get("confidence_score", 0) < 0.7:
            raise ValidationError("Low confidence score")
            
        return output
    except ValidationError as e:
        logger.error(f"Agent output validation failed: {e}")
        raise
```

## Performance Optimization

### Caching Strategy
```python
# Cache frequently accessed data
@lru_cache(maxsize=128)
def get_helm_chart_info(chart_name: str) -> dict:
    """Cache Helm chart metadata"""
    pass

@lru_cache(maxsize=64)
def get_dashboard_metadata(dashboard_id: str) -> dict:
    """Cache Grafana dashboard information"""
    pass
```

### Parallel Processing
```python
# Execute independent agents in parallel
async def parallel_agent_execution(agents: List[str], shared_state: dict):
    tasks = []
    for agent_name in agents:
        if can_run_parallel(agent_name):
            task = asyncio.create_task(execute_agent(agent_name, shared_state))
            tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return process_parallel_results(results)
```

## Integration with LangGraph

### Graph Node Definition
```python
from langgraph import StateGraph
from langgraph.prebuilt import ToolNode

# Create workflow graph
workflow = StateGraph(WorkflowState)

# Add agent nodes
workflow.add_node("workload_detection", workload_detection_node)
workflow.add_node("plan_generation", monitoring_plan_generation_node)
workflow.add_node("plan_evaluation", monitoring_plan_evaluation_node)
workflow.add_node("dashboard_recommendation", dashboard_recommendation_node)

# Add tool nodes
workflow.add_node("tools", ToolNode(tools))

# Define transitions
workflow.add_edge("workload_detection", "plan_generation")
workflow.add_conditional_edges(
    "plan_evaluation",
    should_improve_plan,
    {"improve": "plan_generation", "approve": "dashboard_recommendation"}
)
```

### State Management
```python
class WorkflowState(TypedDict):
    """Shared state across all agents"""
    session_id: str
    phase: str
    cluster_data: List[dict]
    detected_workloads: List[dict]
    selected_workloads: List[dict]
    monitoring_plan: str
    evaluation_feedback: str
    structured_instructions: List[dict]
    recommended_dashboards: List[dict]
    error: Optional[str]
    metadata: dict
```
