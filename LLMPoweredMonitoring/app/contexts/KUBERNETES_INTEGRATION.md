# Kubernetes Integration and Deployment Guide

## Overview

The system integrates deeply with Kubernetes to discover workloads, analyze services, and deploy monitoring infrastructure automatically. This document covers the complete K8s integration architecture, workload discovery, deployment automation, and operational procedures.

## Kubernetes Client Architecture

### Client Implementation
**File**: `k8s/client.py`

```python
class K8sClient:
    """Kubernetes API client for service discovery and workload analysis."""
    
    def __init__(self, kube_config: str = None):
        """Initialize client with multiple authentication methods."""
        if kube_config:
            config.load_kube_config(config_file=kube_config)
        else:
            config.load_incluster_config()  # For pod-based execution
            
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
```

### Authentication Methods
The system supports multiple authentication patterns:

1. **In-cluster authentication** (when running as pod):
   ```python
   config.load_incluster_config()
   # Uses ServiceAccount token + CA cert from /var/run/secrets/kubernetes.io/
   ```

2. **Kubeconfig file** (for local development):
   ```python
   config.load_kube_config(config_file="/path/to/kubeconfig")
   # Supports multiple contexts and authentication methods
   ```

3. **Explicit configuration** (for CI/CD):
   ```python
   configuration = client.Configuration()
   configuration.host = "https://cluster-api-server"
   configuration.api_key = {"authorization": "Bearer token"}
   ```

## Workload Model and Discovery

### Workload Data Model
**File**: `k8s/client.py`

```python
class Workload(BaseModel):
    """Represents a Kubernetes workload (service) with monitoring context."""
    name: str                                           # Service name
    namespace: str                                      # Kubernetes namespace
    metadata_name: str                                  # Full metadata name
    metadata_labels: Optional[Dict[str, str]] = None   # Service labels
    service_type: str                                   # ClusterIP, NodePort, LoadBalancer
    service_ports: List[Dict[str, Any]]                # Port specifications
    service_annotations: Optional[Dict[str, str]] = None # Service annotations
    
    # OSS Detection Results
    pretty_name: Optional[str] = None                  # Human-readable OSS type (e.g., "postgresql")
    is_oss: Optional[bool] = None                      # OSS classification result
    monitoring_config: Optional[Dict] = None           # Monitoring-specific configuration
```

### Service Discovery Implementation
```python
def get_services(self) -> Dict[str, Workload]:
    """Discover all services across cluster with OSS potential."""
    
    # Get all services from all namespaces
    services = self.v1.list_service_for_all_namespaces()
    workloads = {}
    
    for service in services.items:
        # Apply filtering logic
        if self._should_skip_service(service):
            continue
            
        # Convert to Workload model
        workload = self._service_to_workload(service)
        workloads[f"{workload.name}-{workload.namespace}"] = workload
        
    return workloads

def _should_skip_service(self, service) -> bool:
    """Determine if service should be skipped for monitoring."""
    # Skip system namespaces
    if service.metadata.namespace in ['kube-system', 'kube-public', 'kube-node-lease']:
        return True
        
    # Skip services without selectors (external services)
    if not service.spec.selector:
        return True
        
    # Skip Kubernetes API server
    if service.metadata.name == 'kubernetes':
        return True
        
    return False
```

### Service-to-Workload Conversion
```python
def _service_to_workload(self, service) -> Workload:
    """Convert Kubernetes Service to Workload model."""
    
    # Extract port information
    service_ports = []
    for port in service.spec.ports or []:
        service_ports.append({
            'name': port.name,
            'port': port.port,
            'target_port': port.target_port,
            'protocol': port.protocol
        })
    
    return Workload(
        name=service.metadata.name,
        namespace=service.metadata.namespace,
        metadata_name=f"{service.metadata.name}.{service.metadata.namespace}",
        metadata_labels=service.metadata.labels or {},
        service_type=service.spec.type,
        service_ports=service_ports,
        service_annotations=service.metadata.annotations or {}
    )
```

## OSS Workload Detection

### Detection Algorithm
**File**: `ai/graphs.py` - `detect_oss_workloads()`

The system uses AI-powered analysis to identify OSS components:

```python
def detect_oss_workloads(workflow: Workflow) -> dict[str, Workload]:
    """Detect OSS workloads using AI agent with specialized knowledge."""
    
    detected_workloads = workflow.detected_workloads
    if not detected_workloads:
        return {"detected_oss_workloads": {}}
    
    # Generate analysis prompt with workload data
    analysis_prompt = tools.generate_workload_detection_analysis_prompt(detected_workloads)
    
    # Run AI agent with OSS detection expertise
    response, tool_calls = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        model=models.llm_4o,
        tools=[],  # No external tools needed for detection
        agent_prompt=prompts.NEW_OSS_DETECTION_PROMPT
    )
```

### OSS Detection Patterns
The AI agent is trained to recognize common OSS patterns:

#### 1. Database Systems
```python
DATABASE_PATTERNS = {
    "postgresql": {
        "ports": [5432],
        "image_patterns": ["postgres", "postgresql", "bitnami/postgresql"],
        "labels": ["app.kubernetes.io/name=postgresql", "app=postgres"],
        "monitoring_approach": "prometheus-postgres-exporter"
    },
    "mysql": {
        "ports": [3306],
        "image_patterns": ["mysql", "mariadb", "percona"],
        "labels": ["app.kubernetes.io/name=mysql", "app=mysql"],
        "monitoring_approach": "prometheus-mysqld-exporter"
    },
    "redis": {
        "ports": [6379],
        "image_patterns": ["redis", "bitnami/redis"],
        "labels": ["app.kubernetes.io/name=redis", "app=redis"],
        "monitoring_approach": "prometheus-redis-exporter"
    }
}
```

#### 2. Message Queue Systems
```python
MESSAGING_PATTERNS = {
    "kafka": {
        "ports": [9092, 9093],
        "image_patterns": ["kafka", "confluentinc", "bitnami/kafka"],
        "labels": ["app.kubernetes.io/name=kafka", "app=kafka"],
        "monitoring_approach": "prometheus-kafka-exporter"
    },
    "rabbitmq": {
        "ports": [5672, 15672],
        "image_patterns": ["rabbitmq", "bitnami/rabbitmq"],
        "labels": ["app.kubernetes.io/name=rabbitmq", "app=rabbitmq"],
        "monitoring_approach": "prometheus-rabbitmq-exporter"
    }
}
```

#### 3. Web Servers and Proxies
```python
WEB_SERVER_PATTERNS = {
    "nginx": {
        "ports": [80, 443, 8080],
        "image_patterns": ["nginx", "nginxinc/nginx-unprivileged"],
        "labels": ["app.kubernetes.io/name=nginx", "app=nginx"],
        "monitoring_approach": "prometheus-nginx-exporter"
    },
    "traefik": {
        "ports": [80, 443, 8080, 8090],
        "image_patterns": ["traefik"],
        "labels": ["app.kubernetes.io/name=traefik", "app=traefik"],
        "monitoring_approach": "built-in-metrics"
    }
}
```

## Deployment Automation System

### Instruction Architecture
**File**: `ai/instructions.py`

The system uses typed instruction objects for deployment automation:

```python
# Base instruction types
class KubectlInstruction(BaseModel):
    """Represents a kubectl command instruction."""
    type: Literal["kubectl"] = "kubectl"
    command: str
    
class HelmInstruction(BaseModel):
    """Represents a helm command instruction."""
    type: Literal["helm"] = "helm" 
    command: str
    
class CreateFileInstruction(BaseModel):
    """Represents a file creation instruction."""
    type: Literal["create_file"] = "create_file"
    filename: str
    content: str
    
class OtherInstruction(BaseModel):
    """Represents any other type of instruction."""
    type: Literal["other"] = "other"
    description: str
    content: str

# Union type for all instruction types
MonitoringInstruction = Union[KubectlInstruction, HelmInstruction, CreateFileInstruction, OtherInstruction]
```

### Instruction Controller
**File**: `ai/deployment/controller.py`

```python
class InstructionController:
    """Manages execution of monitoring deployment instructions."""
    
    def __init__(self, dry_run: bool = False):
        self.instructions: List[MonitoringInstruction] = []
        self.complete_instructions: List[MonitoringInstruction] = []
        self.failed_instructions: List[MonitoringInstruction] = []
        self.dry_run = dry_run
        
    def execute_plan(self, delete: bool = False) -> bool:
        """Execute instructions sequentially with error handling."""
        for i, instruction in enumerate(self.instructions):
            try:
                success = self.execute_instruction(instruction, delete=delete)
                if success:
                    self.complete_instructions.append(instruction)
                else:
                    self.failed_instructions.append(instruction)
                    if not delete:  # Continue cleanup even if some deletions fail
                        break
            except Exception as e:
                self.failed_instructions.append(instruction)
                logger.error(f"Instruction execution failed: {e}")
                if not delete:
                    break
        
        return len(self.failed_instructions) == 0
```

### Command Execution Safety
```python
def _execute_command(self, command: str, timeout: int = 300) -> tuple[bool, str, str]:
    """Execute shell command with safety checks and timeout."""
    
    if self.dry_run:
        printer.info(f"[DRY RUN] Would execute: {command}")
        return True, "dry-run-success", ""
    
    try:
        # Use shlex.split for proper command parsing
        cmd_args = shlex.split(command)
        
        result = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False  # Don't raise exception on non-zero exit
        )
        
        success = result.returncode == 0
        return success, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return False, "", f"Command execution error: {str(e)}"
```

### Rollback Capabilities
```python
def _convert_to_delete_command(self, kubectl_command: str) -> str:
    """Convert kubectl apply/create commands to delete commands."""
    if "apply" in kubectl_command:
        return kubectl_command.replace("apply", "delete")
    elif "create" in kubectl_command:
        return kubectl_command.replace("create", "delete")
    return kubectl_command

def _convert_helm_to_delete_command(self, helm_command: str) -> str:
    """Convert helm install/upgrade commands to uninstall commands."""
    if "install" in helm_command or "upgrade" in helm_command:
        parts = helm_command.split()
        for i, part in enumerate(parts):
            if part in ["install", "upgrade"]:
                parts[i] = "uninstall"
                break
        # Keep only essential parts for uninstall
        return " ".join([p for p in parts if not p.startswith("-") and "/" not in p])
    return helm_command
```

## ServiceMonitor Generation

### Azure Managed Prometheus Integration
**Critical Requirement**: Azure Managed Prometheus requires specific apiVersion:

```yaml
# CORRECT for Azure Managed Prometheus
apiVersion: azmonitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: postgres-monitoring
  namespace: production
spec:
  selector:
    matchLabels:
      app: postgres
  endpoints:
  - port: metrics
    interval: 30s
    path: /metrics
```

### Dynamic ServiceMonitor Generation
```python
def generate_servicemonitor_yaml(workload: Workload, exporter_config: dict) -> str:
    """Generate ServiceMonitor YAML for workload monitoring."""
    
    servicemonitor = {
        "apiVersion": "azmonitoring.coreos.com/v1",  # Azure-specific
        "kind": "ServiceMonitor",
        "metadata": {
            "name": f"{workload.name}-monitoring",
            "namespace": workload.namespace,
            "labels": {
                "app": workload.name,
                "monitoring": "enabled"
            }
        },
        "spec": {
            "selector": {
                "matchLabels": workload.metadata_labels
            },
            "endpoints": [{
                "port": exporter_config.get("metrics_port", "metrics"),
                "interval": exporter_config.get("scrape_interval", "30s"),
                "path": exporter_config.get("metrics_path", "/metrics")
            }]
        }
    }
    
    return yaml.dump(servicemonitor, default_flow_style=False)
```

## Helm Integration

### Chart Repository Management
The system automatically manages Helm repositories:

```python
# Standard repository setup
REQUIRED_REPOSITORIES = {
    "prometheus-community": "https://prometheus-community.github.io/helm-charts",
    "grafana": "https://grafana.github.io/helm-charts",
    "bitnami": "https://charts.bitnami.com/bitnami"
}

def ensure_helm_repositories():
    """Ensure required Helm repositories are added."""
    for repo_name, repo_url in REQUIRED_REPOSITORIES.items():
        commands = [
            f"helm repo add {repo_name} {repo_url}",
            "helm repo update"
        ]
```

### Chart Installation Patterns
```python
def generate_helm_install_command(workload: Workload, chart_config: dict) -> str:
    """Generate Helm install command with proper Azure overrides."""
    
    chart_name = chart_config["chart"]
    release_name = f"{workload.name}-monitoring"
    namespace = workload.namespace
    
    # Base command
    cmd = f"helm install {release_name} {chart_name}"
    cmd += f" --namespace {namespace} --create-namespace"
    
    # Azure-specific overrides
    cmd += " --set serviceMonitor.enabled=true"
    cmd += " --set serviceMonitor.apiVersion=azmonitoring.coreos.com/v1"
    
    # Workload-specific configuration
    if workload.pretty_name == "postgresql":
        cmd += f" --set datasource.host={workload.name}"
        cmd += f" --set datasource.database=postgres"
        cmd += " --set datasource.user=monitoring"
    elif workload.pretty_name == "redis":
        cmd += f" --set redis.host={workload.name}"
        cmd += f" --set redis.port=6379"
    
    return cmd
```

## Monitoring Plan Structure

### Plan-to-Instructions Conversion
**File**: `ai/graphs.py` - `structure_monitoring_deployment_plan()`

```python
def structure_monitoring_deployment_plan(workflow: Workflow) -> dict[str, MonitoringPlan]:
    """Convert markdown monitoring plan to structured instructions."""
    
    if not workflow.monitoring_plan:
        return {"monitoring_plan": None}
    
    markdown_plan = workflow.monitoring_plan.markdown_plan
    
    # Initialize instruction storage
    instructions_storage = []
    add_instruction_tool = tools.create_add_instruction(instructions_storage)
    
    # Use AI agent to parse plan into structured instructions
    response, tool_calls = agent_utils.AgentManager.create_and_run_agent(
        prompt=f"Convert this monitoring plan to structured instructions:\n\n{markdown_plan}",
        model=models.llm_4o,
        tools=[add_instruction_tool],
        agent_prompt=prompts.STRUCTURE_MONITORING_PLAN_PROMPT
    )
    
    # Update plan with structured instructions
    workflow.monitoring_plan.structured_instructions = instructions_storage
    return {"monitoring_plan": workflow.monitoring_plan}
```

### Instruction Parser Tool
```python
def create_add_instruction(instruction_list: list) -> callable:
    """Create tool for adding structured instructions."""
    
    def add_instruction(instruction_type: str, content: str, filename: str = None):
        """Add an instruction to the deployment plan.
        
        Args:
            instruction_type: Type of instruction (kubectl, helm, create_file, other)
            content: Command or content for the instruction
            filename: Filename for create_file instructions
        """
        
        if instruction_type == "kubectl":
            instruction = KubectlInstruction(command=content)
        elif instruction_type == "helm":
            instruction = HelmInstruction(command=content)
        elif instruction_type == "create_file":
            instruction = CreateFileInstruction(filename=filename, content=content)
        elif instruction_type == "other":
            instruction = OtherInstruction(description=content, content=content)
        else:
            raise ValueError(f"Unknown instruction type: {instruction_type}")
            
        instruction_list.append(instruction)
        
    return add_instruction
```

## Deployment Execution

### Safe Command Execution
```python
def deploy_structured_monitoring_plan(workflow: Workflow) -> dict[str, bool]:
    """Execute deployment plan with safety checks and rollback."""
    
    if not workflow.monitoring_plan or not workflow.monitoring_plan.structured_instructions:
        return {"deployment_success": False}
    
    # Initialize controller
    controller = InstructionController(dry_run=False)
    controller.set_instructions(workflow.monitoring_plan.structured_instructions)
    
    # Pre-flight checks
    prerequisites = controller.check_prerequisites()
    if not all(prerequisites.values()):
        missing_tools = [tool for tool, available in prerequisites.items() if not available]
        printer.error(f"Missing required tools: {missing_tools}")
        return {"deployment_success": False}
    
    # Execute deployment
    try:
        success = controller.execute_plan(delete=False)
        
        if success:
            printer.success("Monitoring deployment completed successfully!")
        else:
            printer.error("Deployment failed. Check logs for details.")
            # Optionally trigger rollback
            # controller.execute_plan(delete=True)
            
        return {"deployment_success": success}
        
    except Exception as e:
        printer.error(f"Deployment execution failed: {e}")
        return {"deployment_success": False}
```

### Prerequisites Validation
```python
def check_prerequisites(self) -> dict[str, bool]:
    """Check if required tools are available."""
    tools = {
        "kubectl": self._check_tool_availability("kubectl"),
        "helm": self._check_tool_availability("helm")
    }
    
    for tool, available in tools.items():
        if available:
            printer.info(f"✅ {tool} is available")
        else:
            printer.warning(f"⚠️  {tool} is not available or not in PATH")
            
    return tools

def _check_tool_availability(self, tool: str) -> bool:
    """Check if a command-line tool is available."""
    try:
        result = subprocess.run(
            [tool, "version"], 
            capture_output=True, 
            text=True, 
            timeout=10,
            check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

## RBAC and Security

### Required Permissions
```yaml
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

# ConfigMap and Secret access (for configuration)
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch", "create", "update", "patch"]
```

### Security Best Practices
1. **Principle of Least Privilege**: Only request necessary permissions
2. **Namespace Isolation**: Respect namespace boundaries for deployments
3. **Secret Management**: Never log or expose sensitive configuration
4. **Input Validation**: Validate all Kubernetes resource names and namespaces
5. **Command Injection Prevention**: Use shlex.split() for command parsing

This comprehensive guide covers all aspects of Kubernetes integration, from service discovery to automated deployment, providing a complete reference for understanding and maintaining the system's K8s capabilities.
