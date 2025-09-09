# LLM Powered Monitoring Helm Chart

This Helm chart deploys the LLM Powered Workload Monitoring application on Kubernetes.

## Architecture Overview

The application uses a layered configuration approach:

1. **[`ai/config.py`](../../ai/config.py)** - Defines the `AZURE_OPENAI_MODELS` dictionary that maps model keys to configuration
2. **[`ai/models.py`](../../ai/models.py)** - Uses the config to create LangChain model instances (`llm_o3`, `llm_4o`, `llm_41`, `llm_5`)
3. **Helm Chart** - Provides environment variables that the config reads via `os.getenv()`

### Configuration Flow
```
Helm Chart values → Environment Variables → config.py → models.py → LangChain Models
```

## Prerequisites

- Kubernetes cluster with RBAC enabled
- Helm 3.x
- Azure OpenAI resource with deployed models
- Optional: GitHub token for enhanced Helm chart discovery

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
OPENAI_KEY=your_azure_openai_key_here
OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
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

### Installation with Helm-Managed Secrets

### Complete Installation Example

```bash
helm install llm-monitoring ./chart/llm-powered-monitoring 
  --namespace llm-powered-monitoring 
  --create-namespace 
  --set config.models.AZURE_DEPLOYMENT_4O="production-gpt-4o" 
  --set config.models.AZURE_DEPLOYMENT_5="production-gpt-5" 
  --set config.parameters.AZURE_TEMPERATURE_4O="0.5" 
  --set secrets.openai.create=true 
  --set secrets.openai.data.OPENAI_KEY="your-azure-openai-key" 
  --set secrets.openai.data.OPENAI_ENDPOINT="https://my-resource.openai.azure.com/"
```

## Configuration

### How Configuration Works

The application uses a layered configuration approach:

1. **Helm Chart** sets environment variables in the pod
2. **[`ai/config.py`](../../ai/config.py)** reads these variables via `os.getenv()` with fallback defaults
3. **[`ai/models.py`](../../ai/models.py)** uses the config to create LangChain model instances

```python
# In ai/config.py
AZURE_OPENAI_MODELS = {
    "gpt-4o": {
        "deployment": os.getenv("AZURE_DEPLOYMENT_4O", "gpt-4o"),  # ← From Helm
        "endpoint": os.getenv("OPENAI_ENDPOINT"),                   # ← From Secret  
        "api_key": os.getenv("OPENAI_KEY"),                        # ← From Secret
        "temperature": float(os.getenv("AZURE_TEMPERATURE_4O", "0.3"))
    }
}

# In ai/models.py  
llm_4o = create_azure_model("gpt-4o")  # Creates AzureChatOpenAI instance
```

### Model Configuration Parameters

| Helm Parameter | Environment Variable | Used In | Description | Default |
|---------------|---------------------|---------|-------------|---------|
| `config.models.AZURE_DEPLOYMENT_4O` | `AZURE_DEPLOYMENT_4O` | config.py | GPT-4o deployment name | `gpt-4o` |
| `config.models.AZURE_DEPLOYMENT_5` | `AZURE_DEPLOYMENT_5` | config.py | GPT-5 deployment name | `gpt-5` |  
| `config.models.AZURE_DEPLOYMENT_O3` | `AZURE_DEPLOYMENT_O3` | config.py | O3 deployment name | `o3` |
| `config.models.AZURE_DEPLOYMENT_41` | `AZURE_DEPLOYMENT_41` | config.py | GPT-4.1 deployment name | `gpt-4.1` |
| `config.models.AZURE_API_VERSION` | `AZURE_API_VERSION` | config.py | Azure OpenAI API version | `2024-12-01-preview` |
| `config.parameters.AZURE_TEMPERATURE_4O` | `AZURE_TEMPERATURE_4O` | config.py | GPT-4o temperature | `0.3` |
| `config.parameters.AZURE_TEMPERATURE_41` | `AZURE_TEMPERATURE_41` | config.py | GPT-4.1 temperature | `0.3` |
| `config.parameters.AZURE_REASONING_EFFORT_5` | `AZURE_REASONING_EFFORT_5` | config.py | GPT-5 reasoning effort | `minimal` |

### Required Secrets (from mounted volumes)

| Secret Key | Environment Variable | Used In | Description |
|-----------|---------------------|---------|-------------|
| `OPENAI_KEY` | `OPENAI_KEY` | config.py | Azure OpenAI API key |
| `OPENAI_ENDPOINT` | `OPENAI_ENDPOINT` | config.py | Azure OpenAI resource endpoint |

### Model Instances Created

The application creates these model instances in [`ai/models.py`](../../ai/models.py):

| Variable | Model Key | Uses Config | Description |
|----------|-----------|-------------|-------------|
| `llm_o3` | `"o3"` | `AZURE_OPENAI_MODELS["o3"]` | O3 model instance |
| `llm_4o` | `"gpt-4o"` | `AZURE_OPENAI_MODELS["gpt-4o"]` | GPT-4o model with temperature |
| `llm_41` | `"gpt-4.1"` | `AZURE_OPENAI_MODELS["gpt-4.1"]` | GPT-4.1 model with temperature |
| `llm_5` | `"gpt-5"` | `AZURE_OPENAI_MODELS["gpt-5"]` | GPT-5 model with reasoning effort |

### End-to-End Configuration Example

1. **Deploy with custom model names:**
   ```bash
   helm install llm-monitoring ./chart/llm-powered-monitoring \
     --set config.models.AZURE_DEPLOYMENT_4O="my-custom-gpt4o" \
     --set config.parameters.AZURE_TEMPERATURE_4O="0.7" \
     --set secrets.openai.data.OPENAI_ENDPOINT="https://my-resource.openai.azure.com/"
   ```

2. **Result: Environment variables in pod:**
   ```bash
   AZURE_DEPLOYMENT_4O=my-custom-gpt4o
   AZURE_TEMPERATURE_4O=0.7
   OPENAI_ENDPOINT=https://my-resource.openai.azure.com/
   ```

3. **config.py reads and creates configuration:**
   ```python
   AZURE_OPENAI_MODELS["gpt-4o"] = {
       "deployment": "my-custom-gpt4o",        # from AZURE_DEPLOYMENT_4O
       "endpoint": "https://my-resource.openai.azure.com/",  # from OPENAI_ENDPOINT  
       "temperature": 0.7                      # from AZURE_TEMPERATURE_4O
   }
   ```

4. **models.py creates LangChain instance:**
   ```python
   llm_4o = AzureChatOpenAI(
       azure_deployment="my-custom-gpt4o",
       azure_endpoint="https://my-resource.openai.azure.com/",
       temperature=0.7
   )
   ```

### General Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace.create` | Create namespace | `true` |
| `namespace.name` | Namespace name | `llm-powered-monitoring` |
| `image.repository` | Image repository | `mcr.microsoft.com/azuremonitor/containerinsights/cidev/prometheus-collector/images` |
| `image.tag` | Image tag | `llm-powered-monitoring-7` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `replicaCount` | Number of replicas | `1` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `llm-powered-monitoring-sa` |
| `rbac.create` | Create RBAC resources | `true` |
| `service.enabled` | Enable service | `true` |
| `service.name` | Service name | `llm-powered-monitoring-service` |
| `service.type` | Service type | `ClusterIP` |
| `service.port` | Service port | `8000` |
| `secrets.openai.create` | Create OpenAI secrets via Helm | `false` |
| `secrets.github.create` | Create GitHub secrets via Helm | `false` |

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

2. **Let Helm manage secrets**:
   ```yaml
   secrets:
     openai:
       create: true
       data:
         OPENAI_KEY: "your-azure-openai-key"
         OPENAI_ENDPOINT: "https://your-resource.openai.azure.com/"
   ```
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
