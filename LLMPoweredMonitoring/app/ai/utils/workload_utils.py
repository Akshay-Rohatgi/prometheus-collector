"""Utilities for workload operations and formatting."""

from typing import Dict, List
from k8s import client as k8s_client

def format_workload_info(workload: k8s_client.Workload) -> str:
    """Format workload information into a human-readable string."""
    return f"""
    Workload Information:
    - Name: {workload.name}
    - Namespace: {workload.namespace}
    - Labels: {workload.metadata_labels}
    - Annotations: {workload.service_annotations}
    - Service Type: {workload.service_type}
    - Service Ports: {workload.service_ports}
    """

def filter_workloads(source_workloads: Dict[str, k8s_client.Workload], filter_names: List[str]) -> Dict[str, k8s_client.Workload]:
    """Filter workloads based on a list of names.
    """
    return {
        name: workload
        for name, workload in source_workloads.items()
        if name in filter_names
    }

def get_first_workload(workloads: Dict[str, k8s_client.Workload]) -> tuple[str, k8s_client.Workload]:
    """Get the first workload from a dictionary of workloads."""
    return list(workloads.items())[0]
