# Development and Deployment Guide

## Development Environment Setup

### Prerequisites
- **Python 3.12+** (specified in Dockerfile and requirements)
- **Kubernetes cluster access** with appropriate RBAC permissions
- **Docker** for containerization and development
- **Helm 3.x** for chart management and deployment
- **kubectl** configured for target cluster
- **Azure OpenAI access** with API keys
- **GitHub access** for chart repository integration

### Local Development Setup

#### 1. Environment Preparation
```bash
# Clone repository
git clone <repository-url>
cd prometheus-collector/LLMPoweredMonitoring/app

# Create virtual environment using Python 3.12
python3.12 -m venv env
source env/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

#### 2. Environment Configuration
The system requires multiple environment variables. Create appropriate `.env` files:

**AI Configuration** (`ai/env/.env`):
```bash
# Azure OpenAI Configuration
RASHMI_AZURE_OPENAI_API_KEY=your-azure-openai-key
AKSHAY_AZURE_OPENAI_API_KEY=your-backup-azure-openai-key
OPENAI_KEY=your-openai-key  # Fallback

# Model Configuration
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

**GitHub Integration** (`ai/utils/env/.env`):
```bash
# GitHub API Access for Helm Charts
GITHUB_TOKEN=your-github-token
GITHUB_USER=your-github-username
```

**Application Configuration** (root `.env`):
```bash
# Application Settings
DEBUG=true
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000

# Kubernetes Configuration
K8S_CONFIG_PATH=/path/to/kubeconfig
K8S_CONTEXT=your-cluster-context

# Workflow Configuration
MAX_EVALUATION_ROUNDS=3
OSS_WORKLOAD_EMOJI=📦
```

#### 3. Kubernetes Configuration
Ensure your kubeconfig provides appropriate permissions:
```yaml
# Required RBAC permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-automation
rules:
- apiGroups: [""]
  resources: ["services", "pods", "namespaces"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["monitoring.coreos.com", "azmonitoring.coreos.com"]
  resources: ["servicemonitors", "prometheusrules"]
  verbs: ["create", "get", "list", "watch", "update", "patch", "delete"]
```

#### 4. Start Development Server
```bash
# Method 1: Direct Python execution
python main.py

# Method 2: FastAPI development mode
uvicorn api.routes:app --host 0.0.0.0 --port 8000 --reload

# Method 3: Using the interactor for testing
python interactor.py
```

#### 5. Development Tools and Testing
```bash
# Run specific tests
python tests/ai/test_oss_detection.py
python tests/ai/test_plan_generation.py

# Run plan generation evaluation
python scripts/run_plan_generation_eval.py

# Test specific functionality
python -c "from k8s.client import K8sClient; client = K8sClient(); print(client.get_services())"
```

## Container Build and Deployment

### Docker Configuration
**File**: `Dockerfile`

```dockerfile
FROM python:3.12-bookworm

WORKDIR /app

# Install system dependencies and tools
RUN apt-get update && apt-get install -y gcc apt-transport-https ca-certificates curl gnupg git nodejs npm && rm -rf /var/lib/apt/lists/*

# Install kubectl (latest stable)
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/

# Install helm
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Add prometheus-community repository
RUN helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Clone awesome-prometheus-alerts for alerting rules
RUN git clone https://github.com/samber/awesome-prometheus-alerts.git /opt/awesome-prometheus-alerts

# Install Azure Prometheus rules converter
RUN npm i -g https://gitpkg.now.sh/Azure/prometheus-collector/tools/az-prom-rules-converter?main

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Set command
CMD ["python", "main.py"]
```

### Building the Container
```bash
# Local build
docker build -t llm-powered-monitoring:latest .

# Build with specific tag
docker build -t llm-powered-monitoring:v1.0.0 .

# Multi-platform build (for Azure Container Registry)
docker buildx build --platform linux/amd64,linux/arm64 -t your-registry/llm-powered-monitoring:latest .
```

### Container Registry Integration
```bash
# Azure Container Registry
az acr login --name your-registry
docker tag llm-powered-monitoring:latest your-registry.azurecr.io/llm-powered-monitoring:latest
docker push your-registry.azurecr.io/llm-powered-monitoring:latest

# Microsoft Container Registry (current deployment)
# Image: mcr.microsoft.com/azuremonitor/containerinsights/cidev/prometheus-collector/images:llm-powered-monitoring-6
```

## Kubernetes Deployment

### Namespace Setup
**File**: `manifests/prod/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: llm-powered-monitoring
  labels:
    app: llm-powered-monitoring
    monitoring: enabled
```

### Service Account and RBAC
**File**: `manifests/prod/serviceaccount.yaml`
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: llm-powered-monitoring-sa
  namespace: llm-powered-monitoring
  labels:
    app: llm-powered-monitoring
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: llm-powered-monitoring-role
rules:
- apiGroups: [""]
  resources: ["services", "pods", "namespaces"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["monitoring.coreos.com", "azmonitoring.coreos.com"]
  resources: ["servicemonitors", "prometheusrules"]
  verbs: ["create", "get", "list", "watch", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: llm-powered-monitoring-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: llm-powered-monitoring-role
subjects:
- kind: ServiceAccount
  name: llm-powered-monitoring-sa
  namespace: llm-powered-monitoring
```

### Application Deployment
**File**: `manifests/prod/deployment.yaml`

```yaml
apiVersion: apps/v1 
kind: Deployment
metadata:
  name: llm-powered-monitoring
  namespace: llm-powered-monitoring
  labels:
    app: llm-powered-monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: llm-powered-monitoring
  template:
    metadata:
      labels:
        app: llm-powered-monitoring
    spec:
      serviceAccountName: llm-powered-monitoring-sa
      containers:
      - name: llm-powered-monitoring
        image: mcr.microsoft.com/azuremonitor/containerinsights/cidev/prometheus-collector/images:llm-powered-monitoring-6
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        env:
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        - name: LOG_LEVEL
          value: "INFO"
        volumeMounts:
        - name: openai-secrets
          mountPath: /app/ai/env
          readOnly: true
        - name: github-secrets
          mountPath: /app/ai/utils/env
          readOnly: true
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: openai-secrets
        secret:
          secretName: openai-secrets
      - name: github-secrets
        secret:
          secretName: github-secrets
```

### Secret Management
```yaml
# OpenAI Secrets
apiVersion: v1
kind: Secret
metadata:
  name: openai-secrets
  namespace: llm-powered-monitoring
type: Opaque
stringData:
  .env: |
    RASHMI_AZURE_OPENAI_API_KEY=your-azure-openai-key
    AKSHAY_AZURE_OPENAI_API_KEY=your-backup-azure-openai-key
    OPENAI_KEY=your-openai-key

---
# GitHub Secrets
apiVersion: v1
kind: Secret
metadata:
  name: github-secrets
  namespace: llm-powered-monitoring
type: Opaque
stringData:
  .env: |
    GITHUB_TOKEN=your-github-token
    GITHUB_USER=your-github-username
```

### Service Configuration
**File**: `manifests/prod/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: llm-powered-monitoring
  namespace: llm-powered-monitoring
  labels:
    app: llm-powered-monitoring
spec:
  type: ClusterIP
  selector:
    app: llm-powered-monitoring
  ports:
  - name: http
    port: 80
    targetPort: 8000
    protocol: TCP
```

## Deployment Scripts and Management

### Deployment Script
**File**: `scripts/deploy.sh`
```bash
#!/bin/bash
set -e

NAMESPACE="llm-powered-monitoring"
KUBECTL_CMD="kubectl"

echo "🚀 Deploying LLM-Powered Monitoring System"

# Create namespace
echo "📁 Creating namespace..."
$KUBECTL_CMD apply -f manifests/prod/namespace.yaml

# Create secrets (ensure these exist)
echo "🔑 Checking secrets..."
if ! $KUBECTL_CMD get secret openai-secrets -n $NAMESPACE >/dev/null 2>&1; then
    echo "⚠️  Please create openai-secrets secret manually"
    exit 1
fi

if ! $KUBECTL_CMD get secret github-secrets -n $NAMESPACE >/dev/null 2>&1; then
    echo "⚠️  Please create github-secrets secret manually"
    exit 1
fi

# Deploy RBAC
echo "🔐 Deploying RBAC..."
$KUBECTL_CMD apply -f manifests/prod/serviceaccount.yaml

# Deploy application
echo "🚀 Deploying application..."
$KUBECTL_CMD apply -f manifests/prod/deployment.yaml
$KUBECTL_CMD apply -f manifests/prod/service.yaml

# Wait for deployment
echo "⏳ Waiting for deployment..."
$KUBECTL_CMD wait --for=condition=available --timeout=300s deployment/llm-powered-monitoring -n $NAMESPACE

echo "✅ Deployment completed successfully!"
echo "📊 Check status: kubectl get pods -n $NAMESPACE"
echo "📋 View logs: kubectl logs -f deployment/llm-powered-monitoring -n $NAMESPACE"
```

### Ubuntu Development Container
**File**: `manage-ubuntu-dev.sh`
The system includes a development container setup for Ubuntu environments:

```bash
#!/bin/bash
# Development container management script

NAMESPACE="monitoring-dev"
DEPLOYMENT_NAME="ubuntu-dev"

deploy_container() {
    print_header "Deploying Ubuntu Development Container"
    
    kubectl apply -f manifests/dev/namespace.yaml
    kubectl apply -f manifests/dev/serviceaccount.yaml  
    kubectl apply -f manifests/dev/ubuntu-deployment.yaml
    
    kubectl wait --for=condition=available --timeout=300s deployment/$DEPLOYMENT_NAME -n $NAMESPACE
}

exec_into_container() {
    print_header "Exec into Ubuntu Container"
    kubectl exec -it deployment/$DEPLOYMENT_NAME -n $NAMESPACE -- /bin/bash
}
```

## Configuration Management

### Application Configuration
**File**: `ai/config.py`
```python
from dotenv import load_dotenv
import os

load_dotenv()

# Kubernetes Configuration
K8S_CONFIG_PATH = os.getenv("K8S_CONFIG_PATH", "/home/user/.kube/config")

# Workflow Configuration  
MAX_EVALUATION_ROUNDS = int(os.getenv("MAX_EVALUATION_ROUNDS", "3"))
OSS_WORKLOAD_EMOJI = os.getenv("OSS_WORKLOAD_EMOJI", "📦")

# External Dependencies
AWESOME_ALERTS_BASE_PATH = "/opt/awesome-prometheus-alerts/dist/rules"
```

### Logging Configuration
**File**: `logs/config.py`
The system supports dual-mode logging:
- **Debug mode**: Rich console output for development
- **Production mode**: Structured JSON logging

```python
def setup_logging():
    """Configure logging based on environment."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    
    if debug_mode:
        setup_rich_logging(log_level)
    else:
        setup_json_logging(log_level)
```

### Model Configuration
**File**: `ai/models.py`
```python
# Azure OpenAI Models
llm_o3 = AzureChatOpenAI(
    azure_deployment="o3",
    api_version="2024-12-01-preview",
    azure_endpoint="https://rashmi-openai.openai.azure.com/",
    api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY")
)

llm_5 = AzureChatOpenAI(
    azure_deployment="gpt-5", 
    api_version="2024-12-01-preview",
    azure_endpoint="https://t-arohatgi-5211-resource.cognitiveservices.azure.com/",
    api_key=os.getenv("AKSHAY_AZURE_OPENAI_API_KEY"),
    reasoning_effort="minimal"
)
```

## Production Deployment Considerations

### High Availability
```yaml
# Multiple replicas with anti-affinity
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - llm-powered-monitoring
              topologyKey: kubernetes.io/hostname
```

### Resource Management
```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi
```

### Health Checks and Monitoring
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 60
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 3
```

### Security Considerations

#### 1. Network Policies
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: llm-powered-monitoring-netpol
  namespace: llm-powered-monitoring
spec:
  podSelector:
    matchLabels:
      app: llm-powered-monitoring
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-system
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to: []  # Allow all egress (required for Azure OpenAI, GitHub, K8s API)
```

#### 2. Pod Security Standards
```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: llm-powered-monitoring
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
```

### Ingress Configuration
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: llm-powered-monitoring
  namespace: llm-powered-monitoring
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
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

## Troubleshooting and Debugging

### Common Issues

#### 1. Kubernetes Connection Issues
```bash
# Check kubeconfig
kubectl config current-context
kubectl cluster-info

# Test service account permissions
kubectl auth can-i list services --as=system:serviceaccount:llm-powered-monitoring:llm-powered-monitoring-sa
```

#### 2. Azure OpenAI API Issues
```python
# Test API connectivity
import os
from ai.models import llm_5

response = llm_5.invoke("Test message")
print(response.content)
```

#### 3. Container Issues
```bash
# Check pod status
kubectl get pods -n llm-powered-monitoring

# Check logs
kubectl logs deployment/llm-powered-monitoring -n llm-powered-monitoring --follow

# Exec into container for debugging
kubectl exec -it deployment/llm-powered-monitoring -n llm-powered-monitoring -- /bin/bash
```

### Monitoring and Observability
```yaml
# ServiceMonitor for the monitoring system itself
apiVersion: azmonitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: llm-powered-monitoring
  namespace: llm-powered-monitoring
spec:
  selector:
    matchLabels:
      app: llm-powered-monitoring
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

This comprehensive deployment guide covers development setup, containerization, Kubernetes deployment, configuration management, and production considerations for the LLM-Powered Monitoring System.
