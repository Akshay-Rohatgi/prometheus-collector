# Testing Guide

## Overview

The LLM-Powered Monitoring System includes comprehensive testing frameworks for validating AI agent performance, plan generation quality, and deployment automation. This guide covers all testing methodologies, tools, and best practices.

## Testing Architecture

### Testing Stack
- **DeepEval**: LLM evaluation framework for agent performance
- **Pytest**: Unit testing framework for core functionality  
- **Docker**: Containerized testing environments
- **Kubernetes**: Integration testing with real clusters
- **Azure OpenAI**: Model evaluation and performance testing

### Test Categories
1. **Unit Tests**: Individual component validation
2. **AI Agent Tests**: LLM-powered functionality evaluation
3. **Integration Tests**: End-to-end workflow validation
4. **Performance Tests**: System benchmarking and optimization
5. **Deployment Tests**: Infrastructure automation validation

## AI Agent Testing Framework

### DeepEval Integration
**File**: `tests/ai/metrics/`

The system uses DeepEval for comprehensive LLM evaluation:

```python
from deepeval import evaluate, assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualPrecisionMetric,
    HallucinationMetric
)

# Custom metrics for monitoring-specific evaluation
from tests.ai.metrics.plan_generation import (
    PlanCoherenceMetric,
    TechnicalCorrectnessMetric,
    AzureCompatibilityMetric
)
```

### OSS Detection Testing
**File**: `tests/ai/test_oss_detection.py`

```python
def test_oss_detection():
    """Run end-to-end evaluation of OSS detection capability."""
    
    # Load test workloads from fixtures
    detected_workloads = json_dump_to_workloads("fixtures/workloads.json")
    
    # Create workflow with test data
    workflow = Workflow(detected_workloads=detected_workloads)
    
    # Execute OSS detection
    state = detect_oss_workloads(workflow)
    detected_oss_workloads = state.get("detected_oss_workloads")
    
    # Create evaluation test cases
    oss_detection_e2e_test = create_oss_detection_e2e_test_case(
        valid_workloads_akshay_cluster, 
        list(detected_oss_workloads.keys())
    )
    
    oss_detection_reasoning_test = create_oss_detection_reasoning_test_case(
        input="Detect OSS workloads in the cluster",
        output=workflow.oss_detection_reasoning
    )
    
    # Get evaluation metrics
    metrics = get_all_oss_detection_metrics()
    
    # Run evaluations
    evaluate([oss_detection_e2e_test, oss_detection_reasoning_test], metrics)
```

### Plan Generation Testing
**File**: `tests/ai/test_plan_generation.py`

```python
def test_plan_generation_e2e():
    """Comprehensive plan generation evaluation with multiple workloads."""
    
    # Create test workloads
    test_workloads = create_test_workloads()
    test_cases = []
    
    for workload in test_workloads:
        # Generate actual monitoring plan
        workflow = Workflow(verified_oss_workload=workload)
        result = generate_monitoring_deployment_plan(workflow)
        monitoring_plan = result.get("monitoring_plan")
        
        if monitoring_plan and monitoring_plan.markdown_plan:
            # Create test case for evaluation
            test_case = create_plan_generation_test_case(
                workload_name=workload.name,
                namespace=workload.namespace,
                service_type=workload.service_type,
                ports_info=", ".join([f"{p['name']}:{p['port']}" for p in workload.service_ports]),
                monitoring_plan=monitoring_plan.markdown_plan,
                workload_labels=workload.metadata_labels
            )
            test_cases.append(test_case)
    
    # Run evaluation with custom metrics
    metrics = get_all_plan_generation_metrics()
    for test_case in test_cases:
        assert_test(test_case, metrics)

def create_test_workloads():
    """Create diverse test workload fixtures."""
    return [
        Workload(
            name="postgres-service",
            namespace="production",
            metadata_name="postgres-service.production",
            service_type="ClusterIP",
            service_ports=[{"name": "postgres", "port": 5432, "protocol": "TCP"}],
            metadata_labels={"app": "postgres", "version": "13"},
            pretty_name="postgresql"
        ),
        Workload(
            name="redis-cache",
            namespace="cache",
            metadata_name="redis-cache.cache", 
            service_type="ClusterIP",
            service_ports=[{"name": "redis", "port": 6379, "protocol": "TCP"}],
            metadata_labels={"app": "redis", "tier": "cache"},
            pretty_name="redis"
        ),
        # Additional test workloads...
    ]
```

## Custom Evaluation Metrics

### Plan Generation Metrics
**File**: `tests/ai/metrics/plan_generation/metrics.py`

```python
class PlanCoherenceMetric(BaseMetric):
    """Evaluate logical flow and structure of monitoring plans."""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.model = AzureChatOpenAI(
            azure_deployment="gpt-4o",
            temperature=0.1
        )
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure plan coherence and logical structure."""
        
        prompt = f"""
        Evaluate the coherence and logical structure of this monitoring deployment plan:
        
        Plan: {test_case.actual_output}
        
        Rate on a scale of 0-10 based on:
        1. Logical flow of steps
        2. Proper prerequisite ordering
        3. Clear section organization
        4. Completeness of instructions
        
        Return only a numeric score.
        """
        
        response = self.model.invoke(prompt)
        score = float(response.content.strip()) / 10.0
        
        self.score = score
        self.success = score >= self.threshold
        return score

class TechnicalCorrectnessMetric(BaseMetric):
    """Evaluate technical accuracy of monitoring configurations."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.model = AzureChatOpenAI(
            azure_deployment="gpt-4o",
            temperature=0.1
        )
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure technical correctness of monitoring plan."""
        
        prompt = f"""
        Evaluate the technical correctness of this monitoring plan:
        
        Plan: {test_case.actual_output}
        
        Check for:
        1. Correct Azure Managed Prometheus apiVersion (azmonitoring.coreos.com/v1)
        2. Valid Helm chart references and parameters
        3. Proper service targeting and port configurations
        4. Azure-specific configuration overrides
        5. Security best practices
        
        Rate technical accuracy on a scale of 0-10.
        Return only a numeric score.
        """
        
        response = self.model.invoke(prompt)
        score = float(response.content.strip()) / 10.0
        
        self.score = score
        self.success = score >= self.threshold
        return score

class AzureCompatibilityMetric(BaseMetric):
    """Evaluate Azure Managed Prometheus compatibility."""
    
    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Check Azure-specific requirements."""
        
        plan_content = test_case.actual_output.lower()
        score = 0.0
        
        # Check for Azure-specific apiVersion
        if "azmonitoring.coreos.com/v1" in plan_content:
            score += 0.4
        
        # Check for ServiceMonitor overrides
        if "servicemonitor.apiversion" in plan_content:
            score += 0.3
        
        # Check for proper helm parameter usage
        if "--set" in plan_content and "servicemonitor" in plan_content:
            score += 0.3
        
        self.score = score
        self.success = score >= self.threshold
        return score
```

### OSS Detection Metrics
**File**: `tests/ai/metrics/oss_detection/metrics.py`

```python
class OSS_Detection_E2E_Metric(BaseMetric):
    """End-to-end OSS detection accuracy."""
    
    def __init__(self, expected_workloads: List[str], threshold: float = 0.8):
        self.expected_workloads = set(expected_workloads)
        self.threshold = threshold
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure detection accuracy against known OSS workloads."""
        
        # Extract detected workloads from test case
        detected = set(test_case.actual_output) if isinstance(test_case.actual_output, list) else set()
        
        # Calculate precision, recall, and F1 score
        true_positives = len(detected.intersection(self.expected_workloads))
        false_positives = len(detected - self.expected_workloads)
        false_negatives = len(self.expected_workloads - detected)
        
        if true_positives == 0:
            precision = recall = f1_score = 0.0
        else:
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        self.score = f1_score
        self.success = f1_score >= self.threshold
        return f1_score

class OSS_Detection_Reasoning_Metric(BaseMetric):
    """Evaluate quality of OSS detection reasoning."""
    
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.model = AzureChatOpenAI(azure_deployment="gpt-4o", temperature=0.1)
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Evaluate reasoning quality for OSS detection decisions."""
        
        prompt = f"""
        Evaluate the quality of this OSS detection reasoning:
        
        Input: {test_case.input}
        Reasoning: {test_case.actual_output}
        
        Rate the reasoning quality on a scale of 0-10 based on:
        1. Technical accuracy of OSS identification
        2. Clear explanation of detection criteria
        3. Proper consideration of monitoring potential
        4. Exclusion of non-OSS or non-monitorable services
        
        Return only a numeric score.
        """
        
        response = self.model.invoke(prompt)
        score = float(response.content.strip()) / 10.0
        
        self.score = score
        self.success = score >= self.threshold
        return score
```

## Test Data and Fixtures

### Workload Fixtures
**File**: `tests/fixtures/workloads.json`

```json
{
    "postgres-service.production": {
        "name": "postgres-service",
        "namespace": "production",
        "metadata_name": "postgres-service.production",
        "service_type": "ClusterIP",
        "service_ports": [
            {"name": "postgres", "port": 5432, "protocol": "TCP"}
        ],
        "metadata_labels": {
            "app": "postgres",
            "version": "13",
            "app.kubernetes.io/name": "postgresql"
        },
        "service_annotations": {
            "prometheus.io/scrape": "true",
            "prometheus.io/port": "9187"
        },
        "pretty_name": "postgresql",
        "is_oss": true
    },
    "redis-cache.cache": {
        "name": "redis-cache",
        "namespace": "cache",
        "metadata_name": "redis-cache.cache",
        "service_type": "ClusterIP",
        "service_ports": [
            {"name": "redis", "port": 6379, "protocol": "TCP"}
        ],
        "metadata_labels": {
            "app": "redis",
            "tier": "cache"
        },
        "pretty_name": "redis",
        "is_oss": true
    }
}
```

### Test Case Creation Utilities
**File**: `tests/ai/metrics/plan_generation/test_cases.py`

```python
def create_plan_generation_test_case(
    workload_name: str,
    namespace: str,
    service_type: str,
    ports_info: str,
    monitoring_plan: str,
    workload_labels: dict = None,
    context_info: list = None
) -> LLMTestCase:
    """Create comprehensive test case for plan generation evaluation."""
    
    # Build retrieval context
    context = context_info or []
    context.extend([
        f"Workload: {workload_name}",
        f"Namespace: {namespace}",
        f"Service Type: {service_type}",
        f"Ports: {ports_info}"
    ])
    
    if workload_labels:
        context.append(f"Labels: {workload_labels}")
    
    return LLMTestCase(
        input=f"Generate monitoring plan for {workload_name} ({service_type}) in {namespace} namespace with ports {ports_info}",
        actual_output=monitoring_plan,
        expected_output=f"A comprehensive monitoring plan for {workload_name} with proper structure, prerequisites, and deployment steps",
        retrieval_context=context
    )

def create_simple_plan_generation_test_case(input_description: str, plan_output: str) -> LLMTestCase:
    """Create simple test case for basic plan generation evaluation."""
    return LLMTestCase(
        input=input_description,
        actual_output=plan_output
    )
```

## Running Tests

### Automated Test Execution
**File**: `scripts/run_plan_generation_eval.py`

```python
#!/usr/bin/env python3
"""Simple runner script for plan generation e2e evaluation."""

def main():
    print("=" * 60)
    print("🧪 Plan Generation E2E Evaluation Runner")
    print("=" * 60)
    
    try:
        from tests.ai.test_plan_generation import test_plan_generation_e2e
        results = test_plan_generation_e2e()
        
        if results:
            print("\n" + "=" * 60)
            print("✅ Evaluation completed successfully!")
            print("📊 Check the output above for detailed results.")
        else:
            print("\n" + "=" * 60) 
            print("❌ Evaluation failed or returned no results.")
            
    except Exception as e:
        print(f"\n💥 Evaluation runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Test Commands
```bash
# Run specific AI tests
python tests/ai/test_oss_detection.py
python tests/ai/test_plan_generation.py

# Run evaluation scripts
python scripts/run_plan_generation_eval.py

# Run all tests with pytest
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test categories
pytest tests/ai/ -k "oss_detection" -v
pytest tests/ai/ -k "plan_generation" -v
```

## Integration Testing

### End-to-End Workflow Testing
```python
def test_complete_workflow():
    """Test complete workflow from detection to deployment."""
    
    # Start workflow
    response = requests.get("http://localhost:8000/start")
    assert response.status_code == 200
    
    data = response.json()
    thread_id = data["thread_id"]
    workloads = data["detected_oss_workloads"]
    
    # Select workloads
    selection_payload = {"workload_keys": list(workloads.keys())[:1]}
    response = requests.post(f"http://localhost:8000/select_oss_workloads/{thread_id}", json=selection_payload)
    assert response.status_code == 200
    
    # Generate plan
    generation_payload = {"generate": True}
    response = requests.post(f"http://localhost:8000/generate_monitoring_plan/{thread_id}", json=generation_payload)
    assert response.status_code == 200
    
    # Evaluate plan
    evaluation_payload = {"evaluate": True}
    response = requests.post(f"http://localhost:8000/evaluate_monitoring_plan/{thread_id}", json=evaluation_payload)
    assert response.status_code == 200
    
    # Structure plan
    structure_payload = {"structure": True}
    response = requests.post(f"http://localhost:8000/structure_monitoring_plan/{thread_id}", json=structure_payload)
    assert response.status_code == 200
    
    # Verify structured instructions
    plan_data = response.json()
    instructions = plan_data["structured_plan"]["instructions"]
    assert len(instructions) > 0
    assert any(inst["type"] == "helm" for inst in instructions)
```

### Performance Testing
```python
def test_performance_benchmarks():
    """Benchmark system performance with multiple concurrent workflows."""
    
    import time
    import concurrent.futures
    
    def run_single_workflow():
        start_time = time.time()
        # Execute complete workflow
        # ... workflow implementation ...
        return time.time() - start_time
    
    # Run concurrent workflows
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_single_workflow) for _ in range(10)]
        durations = [future.result() for future in futures]
    
    # Performance assertions
    avg_duration = sum(durations) / len(durations)
    assert avg_duration < 120  # Should complete within 2 minutes
    assert max(durations) < 300  # No workflow should take more than 5 minutes
```

## Continuous Integration

### GitHub Actions Integration
**File**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      run: pytest tests/unit/ -v
    
    - name: Run AI evaluation tests
      env:
        AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
      run: python scripts/run_plan_generation_eval.py
    
    - name: Generate coverage report
      run: pytest tests/ --cov=. --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

## Test Environment Setup

### Local Testing Environment
```bash
# Setup test environment
python -m venv test-env
source test-env/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov deepeval

# Configure test environment variables
export AZURE_OPENAI_API_KEY="test-key"
export K8S_CONFIG_PATH="/path/to/test/kubeconfig"
export DEBUG=true

# Run tests
pytest tests/ -v
```

### Docker Test Environment
```dockerfile
# Dockerfile.test
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
COPY requirements-test.txt .

RUN pip install -r requirements.txt -r requirements-test.txt

COPY . .

CMD ["pytest", "tests/", "-v", "--cov=.", "--cov-report=html"]
```

This comprehensive testing guide provides complete coverage of testing methodologies, frameworks, and best practices for ensuring the reliability and performance of the LLM-Powered Monitoring System.
