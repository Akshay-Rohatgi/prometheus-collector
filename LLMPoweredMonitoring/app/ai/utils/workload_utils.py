"""Utilities for workload operations and formatting."""

from typing import Dict, List
from k8s import client as k8s_client

def format_workload_info(workload: k8s_client.Workload) -> str:
    """Format workload information into a human-readable string."""
    pretty_name_info = ""
    if hasattr(workload, 'pretty_name') and workload.pretty_name:
        pretty_name_info = f"\n    - Pretty Name: {workload.pretty_name}"
    
    return f"""
    Workload Information:
    - Name: {workload.name}{pretty_name_info}
    - Namespace: {workload.namespace}
    - Labels: {workload.metadata_labels}
    - Annotations: {workload.service_annotations}
    - Service Type: {workload.service_type}
    - Service Ports: {workload.service_ports}
    """

def filter_workloads(source_workloads: Dict[str, k8s_client.Workload], filter_data: List[dict]) -> Dict[str, k8s_client.Workload]:
    """Filter workloads based on a list of workload data with pretty names.
    
    Args:
        source_workloads: Dictionary of workloads keyed by name.lower()
        filter_data: List of dicts with 'workload_name' and 'pretty_name' keys
    
    Returns:
        Dictionary of workloads keyed by original workload name
    """
    filtered = {}
    
    for workload_data in filter_data:
        if isinstance(workload_data, dict):
            workload_name = workload_data.get("workload_name", "").lower()
            pretty_name = workload_data.get("pretty_name", "")
        else:
            # Backward compatibility - if it's just a string
            workload_name = workload_data.lower()
            pretty_name = workload_name
        
        # Find workload by name in source_workloads
        if workload_name in source_workloads:
            workload = source_workloads[workload_name]
            # Set the pretty_name on the workload object for display purposes
            workload.pretty_name = pretty_name
            # Use original workload name as the key (NOT pretty name)
            filtered[workload_name] = workload
    
    return filtered


def get_first_workload(workloads: Dict[str, k8s_client.Workload]) -> tuple[str, k8s_client.Workload]:
    """Get the first workload from a dictionary of workloads."""
    return list(workloads.items())[0]
