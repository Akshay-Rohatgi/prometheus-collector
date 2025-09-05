# Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting information for the LLM-Powered Monitoring System, covering common issues, diagnostic procedures, and resolution strategies.

## Common Issues and Solutions

### 1. Kubernetes Connection Issues

#### Problem: Cannot connect to Kubernetes cluster
```
Error: Failed to connect to Kubernetes cluster
```

**Diagnostic Steps:**
```bash
# Check kubeconfig validity
kubectl config current-context
kubectl cluster-info

# Test authentication
kubectl auth can-i list services

# Verify service account (if running in cluster)
kubectl get serviceaccount llm-powered-monitoring-sa -n llm-powered-monitoring
kubectl describe serviceaccount llm-powered-monitoring-sa -n llm-powered-monitoring
```

**Solutions:**
1. **Invalid kubeconfig:**
   ```bash
   # Update kubeconfig path
   export K8S_CONFIG_PATH="/correct/path/to/kubeconfig"
   
   # Or copy kubeconfig to default location
   cp /path/to/kubeconfig ~/.kube/config
   ```

2. **Expired credentials:**
   ```bash
   # Refresh Azure AKS credentials
   az aks get-credentials --resource-group myResourceGroup --name myAKSCluster
   
   # Refresh AWS EKS credentials
   aws eks update-kubeconfig --region us-west-2 --name my-cluster
   ```

3. **RBAC permissions:**
   ```bash
   # Apply required RBAC
   kubectl apply -f manifests/prod/serviceaccount.yaml
   
   # Verify permissions
   kubectl auth can-i list services --as=system:serviceaccount:llm-powered-monitoring:llm-powered-monitoring-sa
   ```

#### Problem: No workloads detected
```
Error: No OSS workloads detected in cluster
```

**Diagnostic Steps:**
```bash
# Check if services exist
kubectl get services --all-namespaces

# Verify namespace filtering
kubectl get services -n production
kubectl get services -n staging

# Check service labels and annotations
kubectl describe service postgres-service -n production
```

**Solutions:**
1. **Namespace filters too restrictive:**
   ```python
   # Update namespace filtering in configuration
   NETWORK_CONFIG = {
       "allowed_namespaces": ["*"],  # Allow all namespaces
       "excluded_namespaces": ["kube-system", "kube-public"]
   }
   ```

2. **Services lack OSS patterns:**
   ```bash
   # Add labels to identify OSS services
   kubectl label service postgres-service app.kubernetes.io/name=postgresql
   kubectl annotate service postgres-service prometheus.io/scrape=true
   ```

### 2. Azure OpenAI API Issues

#### Problem: API authentication failures
```
Error: Azure OpenAI API authentication failed
```

**Diagnostic Steps:**
```python
# Test API connectivity
from ai.models import llm_4o
response = llm_4o.invoke("Test message")
print(response.content)
```

**Solutions:**
1. **Invalid API keys:**
   ```bash
   # Verify API key format
   echo $RASHMI_AZURE_OPENAI_API_KEY | wc -c  # Should be 32+ characters
   
   # Test key validity
   curl -H "api-key: $RASHMI_AZURE_OPENAI_API_KEY" \
        "https://rashmi-openai.openai.azure.com/openai/deployments?api-version=2024-12-01-preview"
   ```

2. **Incorrect endpoint configuration:**
   ```python
   # Update model configuration
   llm_4o = AzureChatOpenAI(
       azure_deployment="gpt-4o",
       api_version="2024-12-01-preview",
       azure_endpoint="https://correct-endpoint.openai.azure.com/",
       api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY")
   )
   ```

3. **Rate limiting:**
   ```python
   # Implement retry with exponential backoff
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
   def call_openai_with_retry():
       return llm_4o.invoke("Test message")
   ```

#### Problem: Model deployment not found
```
Error: The API deployment for this resource does not exist
```

**Solutions:**
1. **Verify deployment names:**
   ```bash
   # List available deployments
   az cognitiveservices account deployment list \
     --resource-group myResourceGroup \
     --name myOpenAIResource
   ```

2. **Update deployment names in configuration:**
   ```python
   # Use correct deployment names
   DEPLOYMENT_NAMES = {
       "gpt-4o": "actual-gpt-4o-deployment-name",
       "gpt-5": "actual-gpt-5-deployment-name"
   }
   ```

### 3. Workflow State Issues

#### Problem: Workflow stuck in phase
```
Status: Workflow stuck in 'monitoring-plan-generation' phase
```

**Diagnostic Steps:**
```bash
# Check workflow status
curl http://localhost:8000/status/{thread_id}

# Check application logs
kubectl logs deployment/llm-powered-monitoring -n llm-powered-monitoring --tail=100

# Check for hanging processes
ps aux | grep python
```

**Solutions:**
1. **Clear workflow state:**
   ```python
   # Reset workflow (in development)
   import requests
   response = requests.post(f"http://localhost:8000/reset/{thread_id}")
   ```

2. **Manual phase advancement:**
   ```python
   # Force phase transition (emergency use)
   import asyncio
   from api.routes import _workflows
   
   async def force_phase_update(thread_id, new_phase):
       async with _workflows_lock:
           if thread_id in _workflows:
               _workflows[thread_id].phase = new_phase
   ```

#### Problem: Interrupt not being handled
```
Error: Workflow waiting for user input but no response
```

**Solutions:**
1. **Manual interrupt resolution:**
   ```python
   # Resume workflow with user input
   from langgraph.types import Command
   
   workflow_graph = get_graph()
   result = workflow_graph.invoke(
       Command(resume=True, value={"user_input": True}),
       config
   )
   ```

2. **Check interrupt configuration:**
   ```python
   # Ensure interrupts are properly configured
   def select_oss_workloads(workflow: Workflow) -> dict:
       user_selection = interrupt({"message": "Select workloads", "options": workload_keys})
       return {"selected_workload": user_selection}
   ```

### 4. AI Agent Issues

#### Problem: Agent responses are empty or invalid
```
Error: Agent response was empty or invalid
```

**Diagnostic Steps:**
```python
# Enable detailed logging
import logging
logging.getLogger("ai.graphs").setLevel(logging.DEBUG)

# Test agent directly
from ai.utils.agent_utils import AgentManager
response, tool_calls = AgentManager.create_and_run_agent(
    prompt="Test prompt",
    model=llm_4o,
    tools=[],
    agent_prompt="You are a helpful assistant."
)
print(f"Response: {response}")
print(f"Tool calls: {tool_calls}")
```

**Solutions:**
1. **Model parameter adjustment:**
   ```python
   # Increase max_tokens for longer responses
   llm_4o = AzureChatOpenAI(
       azure_deployment="gpt-4o",
       max_tokens=4000,  # Increased from default
       temperature=0.3
   )
   ```

2. **Prompt engineering fixes:**
   ```python
   # Make prompts more specific and structured
   enhanced_prompt = f"""
   You are an expert DevOps engineer. Your task is to {specific_task}.
   
   Context: {relevant_context}
   
   Requirements:
   1. Specific requirement 1
   2. Specific requirement 2
   
   Please provide a detailed response following this structure:
   1. Analysis
   2. Recommendations
   3. Implementation steps
   """
   ```

3. **Tool call debugging:**
   ```python
   # Add tool call validation
   def validate_tool_calls(tool_calls):
       for call in tool_calls:
           if not call.get('function'):
               logger.warning(f"Invalid tool call: {call}")
               return False
       return True
   ```

#### Problem: Plan evaluation failing
```
Error: Plan evaluation failed - critic agent not responding
```

**Solutions:**
1. **Simplify evaluation criteria:**
   ```python
   # Use simpler evaluation prompt
   basic_evaluation_prompt = f"""
   Review this monitoring plan and determine if it's acceptable (yes/no):
   
   Plan: {monitoring_plan}
   
   Check for:
   - Basic structure and readability
   - Includes installation commands
   - Uses Azure-compatible configuration
   
   Respond with: "APPROVED" or "NEEDS_IMPROVEMENT: [specific issues]"
   """
   ```

2. **Fallback evaluation:**
   ```python
   # Auto-approve after timeout
   def evaluate_with_fallback(workflow: Workflow) -> dict:
       try:
           return evaluate_monitoring_deployment_plan(workflow)
       except Exception as e:
           logger.warning(f"Evaluation failed, auto-approving: {e}")
           return {
               "monitoring_plan_feedback": MonitoringFeedback(
                   critic_approved=True,
                   feedback_text="Auto-approved due to evaluation failure",
                   round_count=1
               )
           }
   ```

### 5. Deployment Issues

#### Problem: Helm commands failing
```
Error: helm command failed with exit code 1
```

**Diagnostic Steps:**
```bash
# Test helm connectivity
helm version
helm repo list

# Check repository access
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Test specific chart
helm show chart prometheus-community/prometheus-postgres-exporter
```

**Solutions:**
1. **Repository issues:**
   ```bash
   # Clean and re-add repositories
   helm repo remove prometheus-community
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   ```

2. **Network connectivity:**
   ```bash
   # Test network access from pod
   kubectl exec -it deployment/llm-powered-monitoring -n llm-powered-monitoring -- \
     curl -I https://prometheus-community.github.io/helm-charts/index.yaml
   ```

3. **Permissions issues:**
   ```bash
   # Verify RBAC for Helm operations
   kubectl auth can-i create deployments --as=system:serviceaccount:llm-powered-monitoring:llm-powered-monitoring-sa
   ```

#### Problem: kubectl commands failing
```
Error: kubectl apply failed - forbidden
```

**Solutions:**
1. **Update RBAC permissions:**
   ```yaml
   # Add missing permissions
   - apiGroups: ["azmonitoring.coreos.com"]
     resources: ["servicemonitors"]
     verbs: ["create", "update", "patch", "delete"]
   ```

2. **Namespace issues:**
   ```bash
   # Ensure namespace exists
   kubectl create namespace production
   
   # Or use --create-namespace flag
   kubectl apply -f servicemonitor.yaml --create-namespace -n production
   ```

### 6. GitHub Integration Issues

#### Problem: Cannot fetch chart information
```
Error: Failed to fetch chart from GitHub API
```

**Diagnostic Steps:**
```python
# Test GitHub API access
import requests
headers = {"Authorization": f"token {github_token}"}
response = requests.get(
    "https://api.github.com/repos/prometheus-community/helm-charts/contents/charts",
    headers=headers
)
print(response.status_code, response.json())
```

**Solutions:**
1. **API rate limiting:**
   ```python
   # Implement rate limiting
   import time
   from functools import wraps
   
   def rate_limit(calls_per_minute=60):
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               time.sleep(60 / calls_per_minute)
               return func(*args, **kwargs)
           return wrapper
       return decorator
   ```

2. **Authentication issues:**
   ```bash
   # Verify token permissions
   curl -H "Authorization: token $GITHUB_TOKEN" \
        https://api.github.com/user
   
   # Update token scopes if needed (repo access required)
   ```

## Diagnostic Commands

### System Health Check
```bash
#!/bin/bash
# health_check.sh - Comprehensive system health check

echo "=== LLM-Powered Monitoring System Health Check ==="

# 1. API Health
echo "1. Testing API health..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/)
if [ "$API_RESPONSE" = "200" ]; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed (HTTP $API_RESPONSE)"
fi

# 2. Kubernetes Connectivity
echo "2. Testing Kubernetes connectivity..."
if kubectl cluster-info > /dev/null 2>&1; then
    echo "✅ Kubernetes connection successful"
    kubectl get nodes --no-headers | wc -l | xargs echo "   Nodes available:"
else
    echo "❌ Kubernetes connection failed"
fi

# 3. Azure OpenAI Connectivity
echo "3. Testing Azure OpenAI connectivity..."
python3 -c "
try:
    from ai.models import llm_4o
    response = llm_4o.invoke('test')
    print('✅ Azure OpenAI connection successful')
except Exception as e:
    print(f'❌ Azure OpenAI connection failed: {e}')
"

# 4. Required Tools
echo "4. Checking required tools..."
for tool in kubectl helm python3; do
    if command -v $tool > /dev/null 2>&1; then
        echo "✅ $tool is available"
    else
        echo "❌ $tool is not available"
    fi
done

# 5. Secret Validation
echo "5. Checking secrets..."
if kubectl get secret openai-secrets -n llm-powered-monitoring > /dev/null 2>&1; then
    echo "✅ OpenAI secrets exist"
else
    echo "❌ OpenAI secrets missing"
fi

if kubectl get secret github-secrets -n llm-powered-monitoring > /dev/null 2>&1; then
    echo "✅ GitHub secrets exist"
else
    echo "❌ GitHub secrets missing"
fi

echo "=== Health Check Complete ==="
```

### Workflow Debugging
```python
#!/usr/bin/env python3
# debug_workflow.py - Workflow state debugging tool

import sys
import json
import requests
from datetime import datetime

def debug_workflow(thread_id):
    """Debug workflow state and provide recommendations."""
    
    print(f"=== Debugging Workflow {thread_id} ===")
    
    # Get workflow status
    try:
        response = requests.get(f"http://localhost:8000/status/{thread_id}")
        if response.status_code == 200:
            status = response.json()
            print(f"📊 Current Phase: {status['phase']}")
            print(f"📊 Active: {status['active']}")
            print(f"📊 Config: {json.dumps(status.get('config', {}), indent=2)}")
        else:
            print(f"❌ Failed to get workflow status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error connecting to API: {e}")
        return
    
    # Phase-specific debugging
    current_phase = status['phase']
    
    if current_phase == "workload-detection":
        print("\n🔍 Workload Detection Debugging:")
        print("- Check Kubernetes connectivity")
        print("- Verify service discovery permissions")
        print("- Check namespace filtering")
        
    elif current_phase == "monitoring-plan-generation":
        print("\n🔍 Plan Generation Debugging:")
        print("- Check Azure OpenAI API connectivity")
        print("- Verify model deployment availability")
        print("- Check tool access (GitHub API)")
        
    elif current_phase == "monitoring-plan-evaluation":
        print("\n🔍 Plan Evaluation Debugging:")
        print("- Check evaluation agent configuration")
        print("- Verify max evaluation rounds setting")
        print("- Check tool call execution")
    
    # Provide next steps
    print(f"\n🔧 Recommended Actions:")
    print(f"1. Check application logs: kubectl logs deployment/llm-powered-monitoring -n llm-powered-monitoring")
    print(f"2. Verify environment variables and secrets")
    print(f"3. Test API endpoints individually")
    print(f"4. Run health check script")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_workflow.py <thread_id>")
        sys.exit(1)
    
    debug_workflow(sys.argv[1])
```

### Log Analysis
```bash
#!/bin/bash
# analyze_logs.sh - Log analysis and error detection

echo "=== Log Analysis ==="

# Get recent logs
kubectl logs deployment/llm-powered-monitoring -n llm-powered-monitoring --tail=100 > /tmp/app_logs.txt

# Check for common error patterns
echo "🔍 Checking for common errors..."

# API errors
if grep -q "HTTP request.*5[0-9][0-9]" /tmp/app_logs.txt; then
    echo "❌ Server errors detected in API logs"
    grep "HTTP request.*5[0-9][0-9]" /tmp/app_logs.txt | tail -5
fi

# OpenAI errors
if grep -q -i "openai.*error\|azure.*error" /tmp/app_logs.txt; then
    echo "❌ OpenAI/Azure errors detected"
    grep -i "openai.*error\|azure.*error" /tmp/app_logs.txt | tail -5
fi

# Kubernetes errors
if grep -q -i "kubernetes.*error\|k8s.*error" /tmp/app_logs.txt; then
    echo "❌ Kubernetes errors detected"
    grep -i "kubernetes.*error\|k8s.*error" /tmp/app_logs.txt | tail -5
fi

# Agent execution errors
if grep -q "Agent execution failed\|agent.*error" /tmp/app_logs.txt; then
    echo "❌ AI agent errors detected"
    grep "Agent execution failed\|agent.*error" /tmp/app_logs.txt | tail -5
fi

# Workflow state issues
if grep -q "Workflow.*failed\|workflow.*error" /tmp/app_logs.txt; then
    echo "❌ Workflow state errors detected"
    grep "Workflow.*failed\|workflow.*error" /tmp/app_logs.txt | tail -5
fi

echo "✅ Log analysis complete"

# Performance analysis
echo "📊 Performance metrics (last 100 log entries):"
echo -n "   Average request duration: "
grep "duration_ms" /tmp/app_logs.txt | \
    sed 's/.*duration_ms": *\([0-9.]*\).*/\1/' | \
    awk '{sum+=$1; count++} END {if(count>0) print sum/count "ms"; else print "N/A"}'

echo -n "   Total API requests: "
grep "HTTP request completed" /tmp/app_logs.txt | wc -l

echo -n "   Error rate: "
error_count=$(grep "ERROR\|CRITICAL" /tmp/app_logs.txt | wc -l)
total_count=$(wc -l < /tmp/app_logs.txt)
if [ $total_count -gt 0 ]; then
    echo "scale=2; $error_count * 100 / $total_count" | bc -l | xargs echo "%"
else
    echo "N/A"
fi

# Cleanup
rm /tmp/app_logs.txt
```

## Performance Optimization

### Memory Issues
```python
# Monitor memory usage
import psutil
import gc

def monitor_memory():
    """Monitor and optimize memory usage."""
    
    # Get current memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"Memory percent: {process.memory_percent():.1f}%")
    
    # Force garbage collection
    gc.collect()
    
    # Memory usage after cleanup
    memory_info_after = process.memory_info()
    print(f"Memory after GC: {memory_info_after.rss / 1024 / 1024:.1f} MB")
```

### API Performance
```python
# Optimize API response times
import time
from functools import wraps

def performance_monitor(func):
    """Decorator to monitor function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start_time
        
        if duration > 30:  # Slow operation threshold
            logger.warning(f"Slow operation detected: {func.__name__} took {duration:.2f}s")
        
        return result
    return wrapper
```

This troubleshooting guide provides comprehensive diagnostic procedures and solutions for common issues in the LLM-Powered Monitoring System, enabling quick issue resolution and system optimization.
