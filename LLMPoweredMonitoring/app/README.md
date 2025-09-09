# LLM Powered Workload Monitoring
LLM Powered Workload Monitoring allows for easy integration of major open-source workloads into Azure managed Prometheus. 

## Application Structure
```yaml
# Core Application Files
main.py                    # FastAPI application entry point and server startup
interactor.py             # Interactive CLI for workflow management and testing
requirements.txt          # Python dependencies and package versions
Dockerfile               # Container build configuration for deployment

# AI and Workflow Management
/ai                      # All agentic capabilities (LangGraph graph, agent management utilities, etc.)
  __init__.py           # AI module initialization
  config.py             # AI model configurations and Azure OpenAI settings
  graphs.py             # LangGraph workflow orchestration and state machine
  instructions.py       # AI agent instruction templates and prompts
  models.py             # Azure OpenAI model instances and configurations
  prompts.py            # Base prompt templates and formatting utilities
  tools.py              # AI agent tools and external integrations
  
  /deployment           # Monitoring configuration deployment controller
    controller.py       # Automated deployment execution and rollback management
    
  /prompts              # System prompts for models
    find_alerting_rules.md           # Prometheus alerting rule generation prompts
    find_grafana_dashboard.md        # Grafana dashboard creation prompts
    monitoring_plan_evaluator.md     # Plan evaluation and improvement prompts
    new_monitoring_plan_generation.md # Monitoring plan generation prompts
    new_oss_detection.md             # OSS workload detection prompts
    structure_monitoring_plan.md     # Plan structuring and formatting prompts
    
  /utils                # Tools for agents
    agent_utils.py      # AI agent management and execution utilities
    gh_utils.py         # GitHub API integration for Helm chart discovery
    print_utils.py      # Output formatting and display utilities
    workload_utils.py   # Kubernetes workload analysis and classification

# API Layer
/api                     # REST API endpoints and request handling
  __init__.py           # API module initialization
  routes.py             # FastAPI routes for workflow management and status

# Core Workflow Engine
/core                    # Workflow state management and orchestration
  __init__.py           # Core module initialization
  workflow.py           # Workflow state definitions and lifecycle management

# Kubernetes Integration
/k8s                     # Kubernetes client and cluster interaction
  __init__.py           # K8s module initialization
  client.py             # Kubernetes API client and service discovery
  filters.py            # Service filtering and workload classification
  tools.py              # Kubernetes utility functions and helpers

# Logging and Monitoring
/logs                    # Centralized logging configuration
  __init__.py           # Logging module initialization
  config.py             # Structured logging setup and configuration

# User Interface
/printer                 # User-facing output and display formatting
  __init__.py           # Printer module initialization
  printer.py            # Rich console output and progress indicators

# Documentation for Coding agents (e.g. Copilot, Cline, etc.)
/contexts                # Comprehensive system documentation
  ARCHITECTURE.md        # Complete system architecture and design patterns
  AI_AGENTS.md           # AI agent workflows and LangGraph implementation
  API_REFERENCE.md       # REST API documentation with schemas
  CONFIGURATION_REFERENCE.md # Environment variables and configuration options
  DEPLOYMENT_GUIDE.md    # Step-by-step deployment procedures
  KUBERNETES_INTEGRATION.md # K8s client implementation and integration
  KNOWLEDGE_INDEX.md     # Documentation navigation and overview
  LOGGING_README.md      # Logging framework and best practices
  TESTING_GUIDE.md       # Testing procedures and DeepEval integration
  TROUBLESHOOTING.md     # Diagnostic tools and issue resolution
  WORKFLOW_STATES.md     # State machine and workflow documentation

# Deployment and Infrastructure
/manifests               # Kubernetes deployment manifests
  /dev                   # Development environment configurations
  /prod                  # Production deployment manifests
    namespace.yaml       # Kubernetes namespace definition
    serviceaccount.yaml  # RBAC service account and permissions
    deployment.yaml      # Application deployment configuration

# Testing Framework
/tests                   # Comprehensive testing suite
  __init__.py           # Test module initialization
  /ai                   # AI agent and workflow testing

# Utility Scripts
/scripts                 # Administrative and utility scripts
  __init__.py           # Scripts module initialization
  run_plan_generation_eval.py # DeepEval testing for plan generation

# Test Files (Root Level)
test_deduplication.py    # Workload deduplication testing
test_display_only.py     # Display-only mode testing
test_pretty_names.py     # Output formatting testing
test_rollback.py         # Deployment rollback testing
tests_print.py           # Print utility testing
```

## Deployment

### Create Azure AI Foundry Resources
1. Deploy the following models, with the following names on the portal: 

| Model Name | Deployment Name  |
|------------|------------------|
| GPT-4o     | gpt-4o           |
| GPT-5      | gpt-5            |
| o3         | o3               |
| GPT-4.1    | gpt-4.1          |

Get the API keys for the models and store them securely.

### Get the GitHub Token
1. Create a Github Personal Access Token (PAT) without any permissions. Unauthenticated requests to the Github API are limited to 60 requests per hour.
2. Store the token securely.

### Deploy with Helm Chart

Basic install
```
helm install llm-monitoring ./chart/llm-powered-monitoring \
  --namespace llm-powered-monitoring \
  --create-namespace \
  --set secrets.openai.create=true \
  --set secrets.openai.data.OPENAI_KEY=your_key \
  --set secrets.openai.data.OPENAI_ENDPOINT=https://your-custom-endpoint.openai.azure.com/ \
  --set secrets.github.create=true \
  --set secrets.github.data.GITHUB_TOKEN=your_token
```

You can run with an empty GitHub token with the below parameters, but you may run into ratelimiting. Unauthenticated requests to the Github API are limited to 60 requests per hour.
```
  --set secrets.github.create=true \
  --set secrets.github.data.GITHUB_TOKEN=""
```

You can find the full list of settings and further documentation on the Helm chart [here](./chart/llm-powered-monitoring/README.md)

### Deploy manually
> Relevant files are located in `app/manifests/prod/`

Create the namespace
```
kubectl apply -f namespace.yaml
```

Create the necessary secrets
```
kubectl create secret generic openai-secrets \
  --from-literal=OPENAI_KEY='<your-openai-key>' \
  -n llm-powered-monitoring

kubectl create secret generic github-secrets \
  --from-literal=GITHUB_TOKEN='<your-github-token>' \
  -n llm-powered-monitoring
```

Create the serviceaccount
```
kubectl apply -f serviceaccount.yaml
```

Create the deployment
```
kubectl apply -f deployment.yaml
```