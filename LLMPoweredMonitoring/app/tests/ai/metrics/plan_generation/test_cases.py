"""Plan Generation Test Case Creation Functions

This module contains all test case creation functions for plan generation testing.
"""

from deepeval.test_case import LLMTestCase


def create_plan_generation_test_case(
    workload_name: str, 
    namespace: str,
    service_type: str,
    ports_info: str,
    monitoring_plan: str,
    workload_labels: dict = None,
    context_info: list = None
) -> LLMTestCase:
    """Create test case for plan generation evaluation.
    
    Args:
        workload_name: Name of the workload
        namespace: Kubernetes namespace
        service_type: Type of Kubernetes service
        ports_info: String description of ports
        monitoring_plan: Generated monitoring plan markdown
        workload_labels: Workload metadata labels (optional)
        context_info: Additional context information (optional)
        
    Returns:
        LLMTestCase: Test case for plan generation metrics evaluation
    """
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
    """Create a simple test case for plan generation evaluation.
    
    Args:
        input_description: Description of the input request
        plan_output: The generated monitoring plan
        
    Returns:
        LLMTestCase: Simple test case for plan generation evaluation
    """
    return LLMTestCase(
        input=input_description,
        actual_output=plan_output
    )
