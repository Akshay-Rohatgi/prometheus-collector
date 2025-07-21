import k8s.client

def generate_workload_detection_analysis_prompt(workloads: dict[str, k8s.client.Workload]) -> str:
    analysis_prompt = """Please analyze the following Kubernetes workloads (services) and identify which ones are major, first-class OSS workloads suitable for Prometheus monitoring.

WORKLOADS TO ANALYZE:
"""
    
    for workload in workloads.values():
        analysis_prompt += f"""
workload_name: {workload.name}
Namespace: {workload.namespace}
Metadata Name: {workload.metadata_name}
Labels: {workload.metadata_labels}
Service Type: {workload.service_type}
Service Ports: {workload.service_ports}
Service Annotations: {workload.service_annotations}
---
"""

    analysis_prompt += """
For each workload you identify as a major OSS project (HIGH confidence), use the add_oss_workload tool to add it to the detected list.
"""

    return analysis_prompt

def generate_monitoring_plan_prompt(workload: k8s.client.Workload) -> str:
    workload_info = f"""
    Workload Information (Service):
    - Name: {workload.name}
    - Namespace: {workload.namespace}
    - Metadata Name: {workload.metadata_name}
    - Labels: {workload.metadata_labels}
    - Service Type: {workload.service_type}
    - Service Ports: {workload.service_ports}
    - Service Annotations: {workload.service_annotations}
    - Is OSS: {workload.is_oss}
    """

    return f"""Please generate a comprehensive monitoring deployment plan for the following workload as per your instructions:

    {workload_info}
    """

