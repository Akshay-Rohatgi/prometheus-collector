import k8s.client

def generate_workload_info(detected_workloads: dict[str, k8s.client.Workload]) -> list[dict]:
    workload_info = []
    for workload in detected_workloads.values():
        workload_details = {
            "name": workload.name,
            "image": workload.image,
            "namespace": workload.namespace,
            "labels": workload.metadata_labels,
            "containers": workload.containers
        }
        workload_info.append(workload_details)

    return workload_info

def generate_workload_detection_analysis_prompt(workload_info: list[dict]) -> str:
    analysis_prompt = f"""Please analyze the following Kubernetes workloads and identify which ones are major, first-class OSS workloads suitable for Prometheus monitoring.

WORKLOADS TO ANALYZE:
"""
    
    for w in workload_info:
        analysis_prompt += f"""
workload_name: {w['name']}
Image: {w['image']}
Namespace: {w['namespace']}
Labels: {w['labels']}
Containers: {w['containers']}
---
"""

    analysis_prompt += """
For each workload you identify as a major OSS project (HIGH confidence), use the add_oss_workload tool to add it to the detected list.
"""

    return analysis_prompt