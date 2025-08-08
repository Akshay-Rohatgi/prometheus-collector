# Development and Deployment Guide

## Development Environment Setup

### Prerequisites
- Python 3.12+
- Kubernetes cluster access (local or remote)
- Docker (for containerization)
- Helm 3.x (for chart deployment)

### Local Development Setup

#### 1. Virtual Environment
```bash
# Create and activate virtual environment
python -m venv env
source env/bin/activate  # Linux/Mac
# or
env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

#### 2. Environment Variables
Create `.env` file in project root:
```bash
# AI Configuration
OPENAI_API_KEY=your-openai-api-key
AI_MODEL=gpt-4
AI_TEMPERATURE=0.1

# Kubernetes Configuration
KUBECONFIG=/path/to/your/kubeconfig
K8S_CONTEXT=your-cluster-context

# Application Configuration
DEBUG=true
LOG_LEVEL=DEBUG
HOST=0.0.0.0
PORT=8000

# Optional: Azure Integration
AZURE_CLIENT_ID=your-client-id
AZURE_TENANT_ID=your-tenant-id
AZURE_SUBSCRIPTION_ID=your-subscription-id
```

#### 3. Start Development Server
```bash
# Run with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Development Tools

#### Code Quality
```bash
# Install development dependencies
pip install black isort flake8 mypy pytest pytest-asyncio

# Format code
black .
isort .

# Lint code
flake8 .
mypy .

# Run tests
pytest tests/ -v
```

#### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Testing Strategy

### Unit Tests
**Location**: `tests/unit/`

```python
# Example test structure
tests/
├── unit/
│   ├── test_workflow.py
│   ├── test_k8s_client.py
│   ├── test_ai_agents.py
│   └── test_instructions.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_k8s_integration.py
└── fixtures/
    ├── mock_k8s_data.yaml
    └── sample_plans.md
```

#### Running Tests
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests (requires cluster access)
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=. --cov-report=html
```

### Mock Kubernetes Data
```python
# tests/fixtures/mock_k8s_data.py
MOCK_SERVICES = [
    {
        "metadata": {
            "name": "postgres-service",
            "namespace": "production",
            "labels": {"app": "postgres"}
        },
        "spec": {
            "ports": [{"name": "postgres", "port": 5432}],
            "selector": {"app": "postgres"}
        }
    }
]
```

### AI Agent Testing
```python
# Mock LLM responses for testing
@pytest.fixture
def mock_llm_response():
    return {
        "detected_workloads": [
            {
                "name": "postgres-service",
                "type": "postgresql",
                "monitoring_potential": "high"
            }
        ]
    }

@patch('ai.models.get_llm_client')
def test_workload_detection(mock_llm, mock_llm_response):
    # Test agent logic with predictable responses
    pass
```

## Container Build and Deployment

### Docker Configuration
**File**: `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl and helm
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl && mv kubectl /usr/local/bin/

RUN curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "main.py"]
```

### Build and Push
```bash
# Build image
docker build -t your-registry/monitoring-automation:latest .

# Test locally
docker run -p 8000:8000 \
    -v ~/.kube:/home/appuser/.kube:ro \
    -e OPENAI_API_KEY=your-key \
    your-registry/monitoring-automation:latest

# Push to registry
docker push your-registry/monitoring-automation:latest
```

## Kubernetes Deployment

### Namespace Setup
**File**: `manifests/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring-automation
  labels:
    app: monitoring-automation
    monitoring: enabled
```

### ServiceAccount and RBAC
**File**: `manifests/serviceaccount.yaml`

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: monitoring-automation
  namespace: monitoring-automation
  annotations:
    # For Azure Workload Identity
    azure.workload.identity/client-id: your-client-id
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: monitoring-automation
rules:
# Service discovery
- apiGroups: [""]
  resources: ["services", "endpoints", "pods", "nodes", "namespaces"]
  verbs: ["get", "list", "watch"]

# Monitoring resources
- apiGroups: ["monitoring.coreos.com"]
  resources: ["servicemonitors", "prometheusrules", "podmonitors"]
  verbs: ["get", "list", "create", "update", "patch", "delete"]

# Application deployment
- apiGroups: ["apps"]
  resources: ["deployments", "daemonsets", "statefulsets"]
  verbs: ["get", "list", "create", "update", "patch"]

# ConfigMaps and Secrets
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "create", "update"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: monitoring-automation
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: monitoring-automation
subjects:
- kind: ServiceAccount
  name: monitoring-automation
  namespace: monitoring-automation
```

### Application Deployment
**File**: `manifests/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: monitoring-automation
  namespace: monitoring-automation
  labels:
    app: monitoring-automation
spec:
  replicas: 2
  selector:
    matchLabels:
      app: monitoring-automation
  template:
    metadata:
      labels:
        app: monitoring-automation
        azure.workload.identity/use: "true"  # For Azure Workload Identity
    spec:
      serviceAccountName: monitoring-automation
      containers:
      - name: monitoring-automation
        image: your-registry/monitoring-automation:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        - name: LOG_LEVEL
          value: "INFO"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: ai-credentials
              key: openai-api-key
        # Azure environment variables (if using Azure integration)
        - name: AZURE_CLIENT_ID
          value: "your-client-id"
        - name: AZURE_TENANT_ID
          value: "your-tenant-id"
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: http
          initialDelaySeconds: 5
          periodSeconds: 10
      # Image pull secrets if using private registry
      imagePullSecrets:
      - name: registry-credentials
---
apiVersion: v1
kind: Service
metadata:
  name: monitoring-automation
  namespace: monitoring-automation
spec:
  selector:
    app: monitoring-automation
  ports:
  - name: http
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### Secrets Management
```bash
# Create AI credentials secret
kubectl create secret generic ai-credentials \
  --from-literal=openai-api-key=your-openai-api-key \
  -n monitoring-automation

# Create registry credentials (if using private registry)
kubectl create secret docker-registry registry-credentials \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  -n monitoring-automation
```

## Production Deployment Considerations

### High Availability
```yaml
# Add pod disruption budget
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: monitoring-automation-pdb
  namespace: monitoring-automation
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: monitoring-automation
```

### Monitoring the Monitor
```yaml
# ServiceMonitor for self-monitoring
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: monitoring-automation
  namespace: monitoring-automation
spec:
  selector:
    matchLabels:
      app: monitoring-automation
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Ingress Configuration
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: monitoring-automation
  namespace: monitoring-automation
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
            name: monitoring-automation
            port:
              number: 80
```

## CI/CD Pipeline

### GitHub Actions Example
**File**: `.github/workflows/deploy.yml`

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio
    
    - name: Run tests
      run: pytest tests/unit/ -v

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
    
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
          ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBECONFIG }}
    
    - name: Deploy to Kubernetes
      run: |
        # Update image in deployment
        kubectl set image deployment/monitoring-automation \
          monitoring-automation=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
          -n monitoring-automation
        
        # Wait for rollout
        kubectl rollout status deployment/monitoring-automation -n monitoring-automation
```

## Configuration Management

### Environment-Specific Configs
```python
# config/environments.py
import os

class BaseConfig:
    DEBUG = False
    LOG_LEVEL = "INFO"
    AI_MODEL = "gpt-4"
    AI_TEMPERATURE = 0.1

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    AI_MODEL = "gpt-4o-mini"  # Cheaper for development

class ProductionConfig(BaseConfig):
    DEBUG = False
    LOG_LEVEL = "WARNING"
    AI_MODEL = "gpt-4"

def get_config():
    env = os.getenv('ENVIRONMENT', 'development')
    if env == 'production':
        return ProductionConfig()
    return DevelopmentConfig()
```

### Health Checks
```python
# Add to main.py
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/ready")
async def readiness_check():
    # Check dependencies
    try:
        # Test K8s connectivity
        k8s_client = get_k8s_client()
        await k8s_client.list_namespaces()
        
        # Test AI client
        ai_client = get_ai_client()
        # Minimal test call
        
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Not ready: {e}")
```

## Operational Procedures

### Backup and Recovery
```bash
# Backup workflow state (if using persistent storage)
kubectl exec -n monitoring-automation deployment/monitoring-automation -- \
  /backup-script.sh

# Recovery from backup
kubectl apply -f backup-restore-job.yaml
```

### Scaling
```bash
# Scale up for high load
kubectl scale deployment monitoring-automation --replicas=5 -n monitoring-automation

# Configure horizontal pod autoscaler
kubectl autoscale deployment monitoring-automation \
  --cpu-percent=70 --min=2 --max=10 -n monitoring-automation
```

### Troubleshooting
```bash
# Check application logs
kubectl logs -n monitoring-automation deployment/monitoring-automation -f

# Debug specific workflow
kubectl exec -it deployment/monitoring-automation -n monitoring-automation -- \
  python -c "from core.workflow import debug_workflow; debug_workflow('session-id')"

# Check resource usage
kubectl top pods -n monitoring-automation
```
