# LLM-Powered Monitoring System Architecture

## System Overview

This is an intelligent monitoring automation system for Azure Kubernetes Service (AKS) with Azure Managed Prometheus. The system uses LLM agents to automatically detect workloads, generate monitoring plans, and deploy monitoring infrastructure with minimal human intervention.

The system operates as a FastAPI-based service that orchestrates AI agents through LangGraph workflows to automate the complete monitoring deployment lifecycle from workload discovery to dashboard recommendations.

## Core Philosophy

The system follows a **human-in-the-loop** approach where:
1. **AI agents handle complex analysis** and plan generation using Azure OpenAI models
2. **Humans make critical decisions** (workload selection, plan approval, deployment confirmation)
3. **Automation handles routine deployment** tasks (Helm installations, kubectl operations)
4. **Each step is transparent and auditable** with structured logging and state persistence
5. **Iterative improvement** through critic agents and multi-round evaluation

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                                │
│  Routes: /start, /select, /generate_plan, /evaluate, /deploy, /dashboards  │
├─────────────────────────────────────────────────────────────────────────────┤
│                    Workflow Orchestration Engine                           │
│              LangGraph State Machine + MemorySaver Checkpoints             │
│    Phases: detection → selection → generation → evaluation → deployment    │
├─────────────────────────────────────────────────────────────────────────────┤
│        AI Agents Layer                │        Kubernetes Layer             │
│    ┌─────────────────────────────┐    │    ┌─────────────────────────────┐   │
│    │ • Workload Detection Agent  │    │    │ • K8sClient Service Mgmt   │   │
│    │ • Plan Generation Agent     │    │    │ • Service Discovery        │   │
│    │ • Plan Evaluation Agent     │    │    │ • Resource Filtering       │   │
│    │ • Dashboard Recommendation  │    │    │ • Deployment Execution     │   │
│    │ • Alerting Rules Agent      │    │    │ • Instruction Controller   │   │
│    └─────────────────────────────┘    │    └─────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Tools & Integrations                             │
│  GitHub API • Helm Charts • Prometheus Exporters • Azure OpenAI Models    │
├─────────────────────────────────────────────────────────────────────────────┤
│                          Infrastructure Layer                              │
│      Azure Managed Prometheus + Grafana + Kubernetes Cluster              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Application Entry Points
- **`main.py`**: Primary FastAPI server startup with logging initialization
- **`interactor.py`**: CLI-based client for interactive workflow management
- **`api/routes.py`**: RESTful API endpoints for workflow operations

### 2. Workflow Orchestration (`core/workflow.py`)
- **WorkflowStatus Model**: Tracks active workflows with thread IDs and phases
- **State Management**: Persistent workflow state across API calls
- **Phase Validation**: Ensures proper workflow progression through defined phases

### 3. AI Agents System (`ai/graphs.py`)
- **Workflow State Model**: Comprehensive state container for all workflow data
- **Agent Nodes**: Specialized functions for each workflow phase
- **LangGraph Integration**: State machine implementation with branching logic
- **Multi-round Evaluation**: Iterative improvement through critic feedback

### 4. Kubernetes Integration (`k8s/`)
- **K8sClient**: Kubernetes API wrapper for service discovery
- **Workload Model**: Pydantic model representing Kubernetes services
- **Service Analysis**: Automated detection of monitoring-worthy workloads

### 5. Deployment System (`ai/deployment/`)
- **InstructionController**: Executes structured deployment commands
- **Instruction Models**: Typed representations of deployment operations
- **Command Execution**: Safe execution of kubectl and Helm commands

## Key Design Patterns

### 1. Agent-Based Architecture
- **Specialized LLM agents** for different tasks (detection, generation, evaluation)
- **Tool integration** for accessing external systems (GitHub, Helm repositories)
- **Prompt engineering** with domain-specific instructions and context
- **Model selection** for optimal performance (GPT-4o, GPT-5, o3 models)

### 2. State Machine Workflow
- **Phase-based progression** through monitoring setup lifecycle
- **Checkpointing** for workflow persistence and recovery using MemorySaver
- **Branching logic** for different workflow paths based on conditions
- **Interrupt handling** for human-in-the-loop decision points

### 3. Structured Output Parsing
- **Markdown to structured data** conversion for monitoring plans
- **Instruction modeling** for deployment automation
- **Validation layers** for plan correctness and Azure compatibility
- **Tool calling** for dynamic information retrieval during generation

### 4. Multi-Model LLM Strategy
- **GPT-5 with reasoning effort** for complex plan generation
- **GPT-4o** for general purpose tasks and evaluations
- **o3 model** for specialized reasoning tasks
- **Model-specific optimization** for different workflow phases

## State Management Architecture

### Workflow State Container
```python
class Workflow(BaseModel):
    thread_id: str
    detected_workloads: dict[str, Workload]
    detected_oss_workloads: dict[str, Workload]
    selected_oss_workload: Workload
    verified_oss_workload: Workload
    monitoring_plan: MonitoringPlan
    monitoring_plan_feedback: MonitoringFeedback
    recommended_dashboards: dict[str, int]
    recommended_alerting_rules: AlertingRules
    deployment_success: bool
```

### Phase Transitions
1. **not-started** → **workload-detection**
2. **workload-detection** → **workload-selection**
3. **workload-selection** → **monitoring-plan-generation**
4. **monitoring-plan-generation** → **monitoring-plan-evaluation**
5. **monitoring-plan-evaluation** → **deployment-confirmation** | **monitoring-plan-generation** (retry)
6. **deployment-confirmation** → **dashboard-recommendation**
7. **dashboard-recommendation** → **alerting-rules-recommendation**
8. **alerting-rules-recommendation** → **completed**

## Error Handling & Resilience

### 1. Graceful Degradation
- **Fallback plans** when AI generation fails
- **Default configurations** for common workload types
- **Timeout handling** for long-running operations

### 2. State Recovery
- **Checkpoint persistence** using LangGraph MemorySaver
- **Workflow resumption** from any phase
- **Error state tracking** and recovery mechanisms

### 3. Validation Layers
- **Input validation** using Pydantic models
- **Output verification** through critic agents
- **Command safety** checks before execution

### 4. Microservice Patterns
- **Async FastAPI** with proper request/response handling
- **Workflow isolation** with unique session IDs
- **RESTful API design** for external integration

## Data Flow

```
User Request → API Endpoint → Workflow State → AI Agent → Tool Execution → State Update → Response
                     ↑                                                            ↓
                  Database ←← Checkpoint Storage ←← LangGraph State ←← Agent Output
```

## Integration Points

### External Systems
- **Kubernetes API** - For workload discovery and deployment
- **Helm Repositories** - For monitoring chart information
- **Azure Managed Prometheus** - Target monitoring system
- **Grafana** - Dashboard recommendations
- **GitHub** - For accessing monitoring configurations

### Internal Components
- **Workflow Engine** (LangGraph) - Orchestrates AI agents
- **State Management** - Persists workflow progress
- **Instruction System** - Structures deployment plans
- **Deployment Controller** - Executes infrastructure changes

## Security Considerations

### Authentication & Authorization
- **Kubernetes RBAC** integration for cluster access
- **Service Account** based permissions
- **API token** validation for external calls

### Data Privacy
- **No persistent storage** of sensitive cluster data
- **Session-based** workflow isolation
- **Audit trails** for all deployment actions

## Scalability Features

### Horizontal Scaling
- **Stateless API servers** with external state storage
- **Async processing** for long-running workflows
- **Session isolation** for concurrent users

### Vertical Scaling
- **Resource-aware** agent execution
- **Configurable LLM models** based on complexity
- **Caching layers** for repeated operations

## Error Handling Strategy

### Graceful Degradation
- **Workflow checkpoints** for recovery
- **Fallback mechanisms** for AI agent failures
- **Manual intervention points** when automation fails

### Monitoring & Observability
- **Structured logging** throughout the system
- **Workflow state tracking** for debugging
- **Performance metrics** for optimization
