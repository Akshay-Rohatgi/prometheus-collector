from deepeval import evaluate, assert_test
from deepeval.test_case import LLMTestCase
from tests.ai.metrics.plan_generation import (
    get_all_plan_generation_metrics,
    create_plan_generation_test_case
)
from ai.graphs import generate_monitoring_deployment_plan, Workflow, MonitoringFeedback
from k8s.client import Workload
import json
import os

def create_test_workloads():
    """Create test workload fixtures using the real Workload model"""
    return [
        Workload(
            name="kafka-service",
            namespace="production", 
            metadata_name="kafka-service",
            metadata_labels={"app": "kafka", "component": "broker"},
            service_type="ClusterIP",
            service_ports=[{"name": "broker", "port": 9092, "protocol": "TCP"}],
            service_annotations={},
            is_oss=True,
        ),

    ]

def create_test_cases():
    """Generate LLMTestCase objects from test workloads"""
    test_cases = []
    workloads = create_test_workloads()
    
    print(f"🔄 Generating monitoring plans for {len(workloads)} test workloads...")
    
    for workload in workloads:
        print(f"  📊 Processing {workload.name} in {workload.namespace}...")
        
        # Create a minimal workflow state for testing
        workflow = Workflow(verified_oss_workload=workload)
        
        try:
            # Generate the actual monitoring plan
            result = generate_monitoring_deployment_plan(workflow)
            monitoring_plan = result.get("monitoring_plan")
            
            if monitoring_plan and monitoring_plan.markdown_plan:
                # Get port info for context
                port_info = ", ".join([f"{p.get('name', 'port')}:{p.get('port')}" for p in workload.service_ports])
                
                test_case = create_plan_generation_test_case(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    service_type=workload.service_type,
                    ports_info=port_info,
                    monitoring_plan=monitoring_plan.markdown_plan,
                    workload_labels=workload.metadata_labels
                )
                test_cases.append(test_case)
                print(f"    ✅ Generated plan for {workload.name}")
            else:
                print(f"    ❌ Failed to generate plan for {workload.name} - no plan returned")
                
        except Exception as e:
            print(f"    💥 Error generating plan for {workload.name}: {e}")
    
    return test_cases

def test_plan_generation():
    """Run end-to-end evaluation of plan generation"""
    print("🚀 Starting plan generation e2e evaluation...")
    
    # Create test cases
    test_cases = create_test_cases()
    print(f"📊 Generated {len(test_cases)} test cases successfully")
    
    if not test_cases:
        print("❌ No test cases generated. Evaluation cannot proceed.")
        return None
    
    # Create metrics (start with coherence only)
    all_metrics = get_all_plan_generation_metrics()
    metrics = [
        all_metrics[0],  # Plan coherence metric
        all_metrics[1]  # Technical correctness metric - enable later
    ]
    
    print(f"📈 Running evaluation with {len(metrics)} metric(s)...")
    
    # Run assert_test for each test case with metrics
    for test_case in test_cases:
        assert_test(test_case, metrics)

if __name__ == "__main__":
    test_plan_generation()
