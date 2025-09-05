# AI Agents and LLM Integration Guide

## Agent Architecture Overview

The system employs specialized AI agents, each with distinct responsibilities and prompt engineering optimizations. All agents are built on top of LangChain/LangGraph with structured output parsing and multi-model LLM strategies for optimal performance.

## Model Configuration and Strategy

### Available Models (`ai/models.py`)
```python
# Azure OpenAI Models with specific use cases
llm_o3 = AzureChatOpenAI(azure_deployment="o3")           # Advanced reasoning
llm_4o = AzureChatOpenAI(azure_deployment="gpt-4o")       # General purpose  
llm_41 = AzureChatOpenAI(azure_deployment="gpt-4.1")      # Legacy compatibility
llm_5 = AzureChatOpenAI(azure_deployment="gpt-5")         # Complex generation
```

### Model Selection Strategy
- **GPT-5**: Complex monitoring plan generation with reasoning_effort="minimal"
- **GPT-4o**: General purpose tasks, evaluations, and tool calling
- **o3**: Advanced reasoning for complex decision making
- **Temperature settings**: 0.3 for consistent, focused outputs

## Core Agent Types

### 1. Workload Detection Agent
**File**: `ai/graphs.py` - `detect_workloads()` and `detect_oss_workloads()`
**Purpose**: Analyze Kubernetes services and identify OSS components suitable for monitoring

#### Technical Implementation
```python
def detect_workloads(workflow: Workflow) -> dict[str, Workload]:
    """Detect workloads in the Kubernetes cluster using K8sClient."""
    client = K8sClient(K8S_CONFIG_PATH)
    detected_workloads = client.get_services()
    
    # Log detected workloads for system tracking
    logger.info("Workloads detected", extra={
        'component': 'ai_graphs',
        'operation': 'detect_workloads',
        'workload_count': len(detected_workloads)
    })
    return {"detected_workloads": detected_workloads}
```

#### OSS Detection Prompt Strategy
```
System Role: Expert Kubernetes administrator and monitoring specialist
Task: Analyze cluster services and identify open-source software worth monitoring
Focus Areas:
- Databases (PostgreSQL, MySQL, Redis, MongoDB, ClickHouse)
- Message queues (RabbitMQ, Kafka, NATS, Pulsar)
- Web servers (Nginx, Apache, Traefik)
- Application frameworks (Node.js, Java applications)
- Storage systems (Elasticsearch, MinIO)
- Exclude: System services, operators, monitoring itself
```

#### Input Processing
- Raw Kubernetes service discovery data from `k8s.client.get_services()`
- Service annotations and labels analysis
- Container image analysis for OSS detection
- Port and protocol inspection for service identification

#### Output Structure
```python
{
    "service_name": {
        "name": "postgres-service",
        "namespace": "production", 
        "pretty_name": "postgresql",  # Human-readable OSS type
        "is_oss": True,
        "monitoring_potential": "high"
    }
}
```

### 2. Monitoring Plan Generator
**File**: `ai/graphs.py` - `generate_monitoring_deployment_plan()`
**Purpose**: Create comprehensive monitoring deployment plans with Azure Managed Prometheus

#### Model Configuration
- **Primary Model**: GPT-5 with reasoning effort for complex planning
- **Fallback Model**: GPT-4o for reliability
- **Temperature**: 0.3 for consistent technical outputs

#### Prompt Engineering Strategy
```
System Role: Senior DevOps engineer specializing in Prometheus monitoring
Context: Azure Managed Prometheus environment with specific apiVersion requirements
Task: Generate deployment plans with structured sections and Azure compatibility
```

#### Tool Integration
The generator has access to specialized tools for accurate plan creation:

```python
tools = [
    tools.get_chart_yaml_version,      # Get latest Helm chart versions
    tools.get_values_yaml_formatted,   # Get chart configuration options
    tools.get_chart_readme,           # Get chart documentation
    tools.search_values_keys          # Search for specific configuration keys
]
```

#### Output Format
- **Markdown structure** with standardized sections
- **Prerequisites section** for service-specific requirements
- **Main installation commands** with proper parameterization
- **Verification steps** for deployment validation
- **Azure-specific configurations** (apiVersion: azmonitoring.coreos.com/v1)

#### Iterative Improvement
The system supports multi-round generation based on critic feedback:
```python
if is_improvement:
    analysis_prompt = f"""
    IMPROVE the existing monitoring deployment plan based on critic feedback.
    
    PREVIOUS PLAN: {previous_plan.markdown_plan}
    CRITIC FEEDBACK: {previous_feedback}
    
    Please ADDRESS the feedback and generate an IMPROVED plan.
    """
```

### 3. Plan Evaluation Agent (Critic)
**File**: `ai/graphs.py` - `evaluate_monitoring_deployment_plan()`
**Purpose**: Evaluate monitoring plans for completeness, correctness, and Azure compatibility

#### Enhanced Evaluation System
```python
def build_enhanced_evaluator_prompt(workload: Workload, exporter_name: str = None) -> str:
    """Build enhanced system prompt with workload context and validation tools."""
```

#### Evaluation Criteria
1. **Service URI Format Validation**
   - Verify service URIs (servicename.namespace.svc.cluster.local)
   - Cross-reference against values.yaml documentation
   - Ensure namespace and service name alignment

2. **Required Configuration Completeness**
   - Verify all necessary values in deployment commands
   - **CRITICAL**: Ensure apiVersion override to "azmonitoring.coreos.com/v1"
   - Check required credentials, database parameters, connection strings
   - Validate configuration parameters for specific exporters

3. **Azure Compatibility**
   - Enforce Azure-specific ServiceMonitor apiVersion
   - Validate Helm parameter overrides
   - Check Azure Managed Prometheus compatibility

#### Tool Access for Validation
```python
tools = [
    tools.get_values_yaml,           # Complete values.yaml with comments
    tools.get_chart_readme,          # Chart documentation and examples
    tools.get_values_yaml_formatted  # Flattened configuration keys
]
```

#### Multi-Round Evaluation
- **Maximum rounds**: Configurable via `MAX_EVALUATION_ROUNDS`
- **Automatic approval**: After max rounds reached
- **Feedback tracking**: Structured feedback with round counting
- **Improvement iteration**: Plans regenerated based on feedback

### 4. Dashboard Recommendation Agent
**File**: `ai/graphs.py` - `reccomend_dashboards()`
**Purpose**: Recommend Grafana dashboards from grafana.com

#### Implementation Strategy
```python
def reccomend_dashboards(workflow: Workflow) -> dict[str, dict[str, int]]:
    """Recommend dashboards based on workload type and monitoring setup."""
    
    workload_name = workflow.verified_oss_workload.name
    exporter_name = workload_name.lower()
    
    # Tool integration for dashboard search
    recommended_dashboards_storage = {}
    add_dashboard_tool = tools.create_add_dashboard_tool(recommended_dashboards_storage)
    
    # Generate recommendations using LLM
    agent_response = agent_utils.AgentManager.create_and_run_agent(
        prompt=f"Find suitable Grafana dashboards for {exporter_name}",
        tools=[tools.fetch_dashboard_from_source, add_dashboard_tool]
    )
```

### 5. Alerting Rules Agent
**File**: `ai/graphs.py` - `reccomend_alerting_rules()`
**Purpose**: Generate Prometheus alerting rules from awesome-prometheus-alerts

#### Tool Integration
```python
tools = [
    tools.get_awesome_rule_index,    # Get available rule categories
    tools.get_awesome_rule,          # Get specific rule content
    tools.create_add_alerting_rules_tool  # Add rules to collection
]
```

#### Rule Selection Strategy
- Query awesome-prometheus-alerts repository
- Match workload type to available rule categories
- Extract and format rules for Azure Managed Prometheus
- Provide installation instructions

## Agent Orchestration (`ai/graphs.py`)

### Workflow State Management
```python
class Workflow(BaseModel):
    """Central state container for all workflow data."""
    thread_id: str
    detected_workloads: dict[str, Workload]
    detected_oss_workloads: dict[str, Workload]
    selected_oss_workload: Workload
    verified_oss_workload: Workload
    monitoring_plan: MonitoringPlan
    monitoring_plan_feedback: MonitoringFeedback
    recommended_dashboards: dict[str, int]
    recommended_alerting_rules: AlertingRules
```

### LangGraph Implementation
```python
def build_graph() -> StateGraph:
    """Build the complete workflow state machine."""
    graph = StateGraph(Workflow)
    
    # Add nodes for each agent
    graph.add_node("detect_workloads", detect_workloads)
    graph.add_node("detect_oss_workloads", detect_oss_workloads)
    graph.add_node("generate_monitoring_deployment_plan", generate_monitoring_deployment_plan)
    graph.add_node("evaluate_monitoring_deployment_plan", evaluate_monitoring_deployment_plan)
    graph.add_node("reccomend_dashboards", reccomend_dashboards)
    graph.add_node("reccomend_alerting_rules", reccomend_alerting_rules)
    
    # Add routing logic
    graph.add_conditional_edges("evaluate_monitoring_deployment_plan", route_after_evaluation)
    
    return graph
```

### Routing Logic
```python
def route_after_evaluation(workflow: Workflow) -> str:
    """Determine next step based on critic feedback."""
    feedback = workflow.monitoring_plan_feedback
    
    if feedback.critic_approved or feedback.round_count >= MAX_EVALUATION_ROUNDS - 1:
        return "approve_monitoring_deployment_plan"
    return "generate_monitoring_deployment_plan"  # Retry generation
```

## Agent Utilities (`ai/utils/`)

### Agent Manager (`ai/utils/agent_utils.py`)
```python
class AgentManager:
    @staticmethod
    def create_and_run_agent(prompt: str, model: AzureChatOpenAI, tools: list, agent_prompt: str):
        """Create and execute agent with specified configuration."""
        
    @staticmethod
    def get_agent_response_content(response) -> str:
        """Extract content from agent response."""
        
    @staticmethod
    def get_agent_tool_calls(response) -> dict:
        """Extract tool calls from agent response."""
```

### Workload Utilities (`ai/utils/workload_utils.py`)
```python
def format_workload_info(workload: Workload) -> str:
    """Format workload information for agent prompts."""
    
    return f"""
    Workload Information:
    - Name: {workload.name}
    - Namespace: {workload.namespace}
    - Service Type: {workload.service_type}
    - Ports: {workload.service_ports}
    - Labels: {workload.metadata_labels}
    - Pretty Name: {workload.pretty_name}
    """
```

## Tool Integration (`ai/tools.py`)

### GitHub Integration Tools
```python
def get_chart_yaml_version(exporter_name: str) -> str:
    """Get latest version from Chart.yaml for prometheus exporter."""
    
def get_values_yaml(exporter_name: str) -> str:
    """Get complete values.yaml with comments from prometheus exporter chart."""
    
def get_chart_readme(exporter_name: str) -> str:
    """Get README.md content for prometheus exporter chart."""
```

### Prometheus Community Tools
```python
def get_values_yaml_formatted(exporter_name: str) -> dict:
    """Get flattened key-value pairs from values.yaml."""
    
def search_values_keys(exporter_name: str, search_pattern: str) -> list:
    """Search for specific configuration keys in values.yaml."""
```

### Dashboard and Alerting Tools
```python
def fetch_dashboard_from_source(dashboard_query: str) -> str:
    """Fetch dashboard information from grafana.com."""
    
def get_awesome_rule_index() -> List[str]:
    """Get list of available alerting rule categories."""
    
def get_awesome_rule(service_name: str) -> Dict[str, str]:
    """Get alerting rules for specific service."""
```

## Configuration (`ai/config.py`)
```python
K8S_CONFIG_PATH = "/path/to/kubeconfig"      # Kubernetes configuration
MAX_EVALUATION_ROUNDS = 3                    # Maximum evaluation iterations
OSS_WORKLOAD_EMOJI = "📦"                   # Display emoji for OSS workloads
```

## Error Handling and Logging

### Structured Logging
All agents use structured logging for system events:
```python
logger.info("Monitoring plan generation started", extra={
    'component': 'ai_graphs',
    'operation': 'generate_monitoring_deployment_plan',
    'workflow_phase': 'monitoring-plan-generation',
    'workload_name': workload.name,
    'is_improvement': is_improvement
})
```

### Fallback Mechanisms
- **Empty response handling**: Generate fallback plans when LLM fails
- **Tool failure recovery**: Continue workflow with limited functionality
- **Timeout handling**: Graceful degradation for long-running operations

### Agent State Recovery
- **Checkpoint persistence**: State saved at each workflow step
- **Resumable execution**: Continue from any workflow phase
- **Error state tracking**: Detailed error information for debugging
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
