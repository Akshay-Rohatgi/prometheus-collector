# LLM Powered Monitoring Helm Chart

This Helm chart deploys the LLM Powered Monitoring application to Kubernetes.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+
- Cluster admin permissions (for ClusterRole/ClusterRoleBinding)

## Installation

### Basic Installation

```bash
# Install with default values
helm install llm-monitoring ./chart/llm-powered-monitoring \
  --namespace llm-powered-monitoring \
  --create-namespace
```

### Installation with External Secrets

The chart expects external secrets by default. Create them before installation:

```bash
# Create namespace first
kubectl create namespace llm-powered-monitoring

# Create OpenAI secrets
kubectl create secret generic openai-secrets \
  --namespace llm-powered-monitoring \
  --from-literal=.env="
RASHMI_AZURE_OPENAI_API_KEY=your_key_here
AKSHAY_AZURE_OPENAI_API_KEY=your_key_here
OPENAI_KEY=your_key_here
"

# Create GitHub secrets
kubectl create secret generic github-secrets \
  --namespace llm-powered-monitoring \
  --from-literal=.env="
GITHUB_TOKEN=your_token_here
GITHUB_USER=your_username_here
"

# Install the chart
helm install llm-monitoring ./chart/llm-powered-monitoring \
  --namespace llm-powered-monitoring
```

### Installation with Chart-Managed Secrets

```bash
helm install llm-monitoring ./chart/llm-powered-monitoring \
  --namespace llm-powered-monitoring \
  --create-namespace \
  --set secrets.openai.create=true \
  --set secrets.openai.data.RASHMI_AZURE_OPENAI_API_KEY=your_key \
  --set secrets.openai.data.AKSHAY_AZURE_OPENAI_API_KEY=your_key \
  --set secrets.github.create=true \
  --set secrets.github.data.GITHUB_TOKEN=your_token
```

## Configuration

The following table lists the configurable parameters and their default values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace.create` | Create namespace | `true` |
| `namespace.name` | Namespace name | `llm-powered-monitoring` |
| `image.repository` | Image repository | `mcr.microsoft.com/azuremonitor/containerinsights/cidev/prometheus-collector/images` |
| `image.tag` | Image tag | `llm-powered-monitoring-6` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `replicaCount` | Number of replicas | `1` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `llm-powered-monitoring-sa` |
| `rbac.create` | Create RBAC resources | `true` |
| `service.enabled` | Enable service | `true` |
| `service.name` | Service name | `llm-powered-monitoring-service` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |
| `secrets.openai.create` | Create OpenAI secrets | `false` |
| `secrets.github.create` | Create GitHub secrets | `false` |

## Upgrading

```bash
helm upgrade llm-monitoring ./chart/llm-powered-monitoring \
  --namespace llm-powered-monitoring
```

## Uninstalling

```bash
helm uninstall llm-monitoring --namespace llm-powered-monitoring

# Optionally delete the namespace
kubectl delete namespace llm-powered-monitoring
```

## Values Override Example

Create a `values-prod.yaml` file:

```yaml
replicaCount: 3

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

probes:
  liveness:
    enabled: true
  readiness:
    enabled: true

secrets:
  openai:
    create: true
    data:
      RASHMI_AZURE_OPENAI_API_KEY: "your-key"
      AKSHAY_AZURE_OPENAI_API_KEY: "your-key"
  github:
    create: true
    data:
      GITHUB_TOKEN: "your-token"
      GITHUB_USER: "your-username"
```

Then install with:

```bash
helm install llm-monitoring ./chart/llm-powered-monitoring \
  --namespace llm-powered-monitoring \
  --create-namespace \
  --values values-prod.yaml
```
