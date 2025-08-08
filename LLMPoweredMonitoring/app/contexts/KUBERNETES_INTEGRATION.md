# Kubernetes Integration and Deployment Guide

## Overview

The system integrates deeply with Kubernetes to discover workloads, analyze services, and deploy monitoring infrastructure. This document covers the K8s integration patterns, deployment automation, and operational procedures.

## Kubernetes Client Architecture

### Client Configuration
**File**: `k8s/client.py`

The system supports multiple authentication methods:
- **In-cluster authentication** (when running as pod)
- **Kubeconfig file** (for local development)
- **Service account tokens** (for CI/CD integration)

```python
# Authentication priority order
AUTH_METHODS = [
    "incluster",      # ServiceAccount token + CA cert
    "kubeconfig",     # ~/.kube/config or KUBECONFIG env
    "token",          # Explicit token + cluster URL
]
```

### Discovery Patterns

#### Service-Centric Discovery
The system focuses on **Services** rather than Deployments/Pods because:
- Services represent stable network endpoints
- Monitoring needs network-accessible metrics endpoints
- Services abstract away pod-level churn
- ServiceMonitor resources target Services

```python
# Service discovery query
def discover_services(namespace_filter: Optional[str] = None) -> List[dict]:
    """
    Discover all services across namespaces with monitoring potential
    
    Filters applied:
    1. Skip system namespaces (kube-system, kube-public, etc.)
    2. Skip services without selectors (external services)
    3. Skip headless services unless explicitly marked
    4. Prioritize services with known OSS patterns
    """
```

#### Metadata Enrichment
For each discovered service, the system collects:
```python
{
    "name": "postgres-service",
    "namespace": "production",
    "cluster_ip": "10.0.100.50",
    "ports": [{"name": "postgres", "port": 5432, "protocol": "TCP"}],
    "selector": {"app": "postgres", "version": "13"},
    "annotations": {"prometheus.io/scrape": "true"},
    "labels": {"app.kubernetes.io/name": "postgresql"},
    "endpoints": [...],  # Backing pods
    "ingress": [...],    # Associated ingress rules
    "related_resources": {
        "deployments": [...],
        "statefulsets": [...],
        "configmaps": [...]
    }
}
```

## Workload Classification System

### OSS Detection Algorithm
**File**: `k8s/tools.py`

The system uses a multi-layered approach to identify OSS components:

#### 1. Image Analysis
```python
OSS_IMAGE_PATTERNS = {
    "postgresql": ["postgres", "postgresql", "bitnami/postgresql"],
    "mysql": ["mysql", "mariadb", "percona"],
    "redis": ["redis", "bitnami/redis"],
    "nginx": ["nginx", "nginxinc/nginx-unprivileged"],
    "mongodb": ["mongo", "mongodb", "bitnami/mongodb"],
    "rabbitmq": ["rabbitmq", "bitnami/rabbitmq"],
    "kafka": ["kafka", "confluentinc", "bitnami/kafka"],
    "elasticsearch": ["elasticsearch", "elastic/elasticsearch"]
}
```

#### 2. Port Pattern Analysis
```python
STANDARD_PORTS = {
    5432: "postgresql",
    3306: "mysql", 
    6379: "redis",
    80: "http",
    443: "https",
    8080: "http-alt",
    9092: "kafka",
    5672: "rabbitmq",
    9200: "elasticsearch",
    27017: "mongodb"
}
```

#### 3. Label Convention Analysis
```python
LABEL_PATTERNS = {
    "app.kubernetes.io/name": "direct_app_name",
    "app.kubernetes.io/component": "component_type", 
    "app": "legacy_app_label",
    "k8s-app": "kubernetes_app_label"
}
```

#### 4. Annotation-Based Discovery
```python
MONITORING_ANNOTATIONS = {
    "prometheus.io/scrape": "explicit_monitoring_intent",
    "prometheus.io/port": "metrics_port",
    "prometheus.io/path": "metrics_endpoint",
    "monitoring.coreos.com/enabled": "operator_monitoring"
}
```

### Blacklist Filtering
**File**: `k8s/filters.py`

To avoid monitoring system components, the following are filtered out:

#### Namespace Blacklists
```python
SYSTEM_NAMESPACES = [
    "kube-system", "kube-public", "kube-node-lease",
    "azure-arc", "azmon-containers-logs", "calico-system",
    "cert-manager", "ingress-nginx", "istio-system",
    "linkerd", "flux-system", "argocd", "tekton-pipelines"
]
```

#### Service Name Patterns
```python
SYSTEM_SERVICE_PATTERNS = [
    r".*-operator.*", r".*-controller.*", r".*-webhook.*",
    r".*-metrics.*", r".*-monitor.*", r"prometheus-.*",
    r"grafana-.*", r"alertmanager-.*", r"jaeger-.*",
    r"kube-.*", r"coredns", r"azure-.*"
]
```

## Deployment Automation

### Instruction System Architecture
**File**: `ai/instructions.py`

The system uses a structured instruction format to represent deployment actions:

#### Instruction Types

##### 1. Helm Instructions
```python
@dataclass
class HelmInstruction:
    action: str  # "install", "upgrade", "uninstall"
    release_name: str
    chart: str  # "prometheus-community/kube-prometheus-stack"
    namespace: str
    values: dict
    version: Optional[str] = None
    timeout: int = 300
    wait: bool = True
    create_namespace: bool = True
```

##### 2. Kubectl Instructions
```python
@dataclass  
class KubectlInstruction:
    action: str  # "apply", "delete", "patch"
    resource_type: str  # "servicemonitor", "prometheusrule"
    name: str
    namespace: str
    manifest: str  # YAML content
    dry_run: bool = False
```

##### 3. File Operations
```python
@dataclass
class FileInstruction:
    action: str  # "create", "update", "delete"
    path: str
    content: str
    permissions: str = "644"
    backup: bool = True
```

### Deployment Controller
**File**: `ai/deployment/controller.py`

#### Execution Engine
```python
class DeploymentController:
    async def execute_instructions(self, instructions: List[Instruction]) -> ExecutionResult:
        """
        Execute deployment instructions with:
        - Pre-flight validation
        - Dependency resolution
        - Rollback on failure
        - Progress tracking
        """
        
        results = []
        rollback_stack = []
        
        try:
            for instruction in instructions:
                # Validate prerequisites
                await self.validate_prerequisites(instruction)
                
                # Execute with monitoring
                result = await self.execute_single_instruction(instruction)
                results.append(result)
                
                # Track for rollback
                if instruction.supports_rollback:
                    rollback_stack.append(instruction.get_rollback_instruction())
                    
        except Exception as e:
            # Execute rollback
            await self.rollback_instructions(rollback_stack)
            raise DeploymentError(f"Deployment failed: {e}")
            
        return ExecutionResult(results)
```

#### Prerequisites Validation
```python
async def validate_prerequisites(self, instruction: Instruction) -> bool:
    """Validate prerequisites before execution"""
    
    checks = {
        HelmInstruction: [
            self.check_helm_binary,
            self.check_chart_availability,
            self.check_namespace_permissions
        ],
        KubectlInstruction: [
            self.check_kubectl_binary,
            self.check_resource_permissions,
            self.check_cluster_connectivity
        ]
    }
    
    for check in checks.get(type(instruction), []):
        if not await check(instruction):
            raise PrerequisiteError(f"Failed prerequisite: {check.__name__}")
            
    return True
```

### ServiceMonitor Generation

#### Template-Based Generation
```python
def generate_servicemonitor(service: dict, monitoring_config: dict) -> str:
    """Generate ServiceMonitor YAML for a service"""
    
    template = {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor", 
        "metadata": {
            "name": f"{service['name']}-monitor",
            "namespace": service['namespace'],
            "labels": {
                "app": service['name'],
                "monitoring": "enabled"
            }
        },
        "spec": {
            "selector": {
                "matchLabels": service['selector']
            },
            "endpoints": generate_endpoints(service, monitoring_config)
        }
    }
    
    return yaml.dump(template, default_flow_style=False)

def generate_endpoints(service: dict, config: dict) -> List[dict]:
    """Generate endpoint configurations for ServiceMonitor"""
    
    endpoints = []
    for port in service['ports']:
        if should_monitor_port(port, config):
            endpoint = {
                "port": port['name'],
                "path": config.get('metrics_path', '/metrics'),
                "interval": config.get('scrape_interval', '30s'),
                "timeout": config.get('scrape_timeout', '10s')
            }
            endpoints.append(endpoint)
            
    return endpoints
```

## Security and RBAC

### Service Account Configuration
**File**: `manifests/serviceaccount.yaml`

Required permissions for the monitoring system:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-automation
rules:
# Discovery permissions
- apiGroups: [""]
  resources: ["services", "endpoints", "pods", "nodes"]
  verbs: ["get", "list", "watch"]

# Monitoring resource management
- apiGroups: ["monitoring.coreos.com"]
  resources: ["servicemonitors", "prometheusrules", "podmonitors"]
  verbs: ["get", "list", "create", "update", "delete"]

# Deployment permissions
- apiGroups: ["apps"]
  resources: ["deployments", "daemonsets", "statefulsets"]
  verbs: ["get", "list"]

# ConfigMap management for monitoring configs
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "create", "update"]
```

### Network Security
- **Internal traffic only** - No external network access required
- **TLS encryption** - All Prometheus scraping uses TLS where possible
- **Secret management** - Sensitive configs stored in Kubernetes secrets
- **Network policies** - Restrict traffic between monitoring components

## Monitoring the Monitor

### Self-Monitoring Configuration
The system monitors itself using:
- **Application metrics** - Custom metrics for workflow success/failure
- **Performance metrics** - Response times, resource usage
- **Error tracking** - Failed deployments, AI agent errors
- **Audit logging** - All cluster modifications logged

```python
# Custom metrics exposed
CUSTOM_METRICS = {
    "workflow_duration_seconds": "Histogram of workflow execution times",
    "agent_invocation_total": "Counter of AI agent invocations",
    "deployment_success_total": "Counter of successful deployments",
    "discovery_services_total": "Gauge of discovered services"
}
```

### Operational Dashboards
- **System Overview** - Workflow status, success rates
- **Performance Monitoring** - Response times, resource usage
- **Error Analysis** - Failed workflows, root cause analysis
- **Capacity Planning** - Resource utilization trends

## Integration with Azure Managed Prometheus

### Azure-Specific Configurations
```yaml
# ServiceMonitor for Azure Managed Prometheus
spec:
  endpoints:
  - port: metrics
    path: /metrics
    interval: 30s
    # Azure Managed Prometheus specific settings
    honorLabels: true
    metricRelabelings:
    - sourceLabels: [__name__]
      targetLabel: __tmp_name
    - sourceLabels: [__tmp_name]
      targetLabel: __name__
      regex: '(.*)'
      replacement: 'azure_${1}'
```

### Workload Identity Integration
```python
# Use Azure AD Workload Identity for authentication
AZURE_CONFIG = {
    "use_workload_identity": True,
    "client_id": os.getenv("AZURE_CLIENT_ID"),
    "tenant_id": os.getenv("AZURE_TENANT_ID"),
    "subscription_id": os.getenv("AZURE_SUBSCRIPTION_ID")
}
```

## Troubleshooting Guide

### Common Issues

#### 1. Service Discovery Problems
- **No services found**: Check RBAC permissions
- **Wrong services detected**: Review blacklist filters
- **Missing metadata**: Verify service annotations/labels

#### 2. Deployment Failures
- **Helm chart not found**: Check repository connectivity
- **Permission denied**: Verify ServiceAccount permissions
- **Resource conflicts**: Check for existing monitoring resources

#### 3. Monitoring Issues
- **No metrics scraped**: Verify ServiceMonitor configuration
- **Authentication failures**: Check service account setup
- **Network connectivity**: Verify pod-to-pod communication

### Diagnostic Commands
```bash
# Check service discovery
kubectl get services --all-namespaces -o wide

# Verify ServiceMonitor creation
kubectl get servicemonitors -A

# Check Prometheus targets
kubectl port-forward -n monitoring prometheus-0 9090:9090
# Navigate to: http://localhost:9090/targets

# View monitoring logs
kubectl logs -n monitoring -l app=monitoring-automation
```
