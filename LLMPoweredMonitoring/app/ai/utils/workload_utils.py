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
        Dictionary of workloads keyed by pretty_name (deduplicated)
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
            # Set the pretty_name on the workload object
            workload.pretty_name = pretty_name
            
            # Deduplication: Only add if we haven't seen this pretty_name before
            if pretty_name not in filtered:
                filtered[pretty_name] = workload
            # If we already have this pretty_name, we keep the first one (no replacement)
    
    return filtered


def deduplicate_oss_workloads(workloads: Dict[str, k8s_client.Workload]) -> Dict[str, k8s_client.Workload]:
    """Remove duplicate workloads that have the same pretty_name.
    
    This is a safety net in case the AI agent detects multiple services 
    for the same OSS project (e.g., kafka-bootstrap and kafka-brokers both as 'kafka').
    We keep the first occurrence.
    
    Args:
        workloads: Dictionary of workloads keyed by pretty_name
    
    Returns:
        Deduplicated dictionary of workloads
    """
    from printer import printer
    from logs import get_logger
    
    logger = get_logger(__name__)
    
    seen_pretty_names = set()
    deduplicated = {}
    removed_count = 0
    
    for key, workload in workloads.items():
        pretty_name = getattr(workload, 'pretty_name', key)
        
        if pretty_name not in seen_pretty_names:
            seen_pretty_names.add(pretty_name)
            deduplicated[key] = workload
        else:
            # Skip duplicates - log what we're removing
            removed_count += 1
            printer.warning(f"🔄 Skipping duplicate '{pretty_name}': {workload.name} (keeping first occurrence)")
            logger.info("Duplicate OSS workload removed", extra={
                'component': 'workload_utils',
                'operation': 'deduplicate_oss_workloads',
                'removed_workload': workload.name,
                'pretty_name': pretty_name,
                'reason': 'duplicate_pretty_name'
            })
    
    if removed_count > 0:
        printer.info(f"🔄 Removed {removed_count} duplicate OSS workload(s)")
        logger.info("OSS workload deduplication completed", extra={
            'component': 'workload_utils', 
            'operation': 'deduplicate_oss_workloads',
            'original_count': len(workloads),
            'final_count': len(deduplicated),
            'removed_count': removed_count
        })
    
    return deduplicated

def get_first_workload(workloads: Dict[str, k8s_client.Workload]) -> tuple[str, k8s_client.Workload]:
    """Get the first workload from a dictionary of workloads."""
    return list(workloads.items())[0]
