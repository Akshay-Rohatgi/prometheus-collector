"""
Deterministic Helm release naming for exporters to enable reliable monitoring state detection.
"""
import re
import hashlib
from typing import Dict

# Conservative length limit to avoid Helm/Kubernetes naming issues
MAX_RELEASE_LEN = 53

def _canonicalize_segment(segment: str) -> str:
    """
    Canonicalize a name segment for use in Helm release names.
    - Convert to lowercase
    - Replace non-alphanumeric characters (except hyphens) with hyphens
    - Collapse consecutive hyphens
    - Trim leading/trailing hyphens
    """
    if not segment:
        return 'x'
    
    s = segment.lower()
    s = re.sub(r'[^a-z0-9-]', '-', s)
    s = re.sub(r'-{2,}', '-', s)
    s = s.strip('-')
    
    return s or 'x'

def create_exporter_release_name(exporter: str, service: str, namespace: str) -> str:
    """
    Create a deterministic Helm release name for an exporter.
    
    Template: azmon-{exporter}-exporter-{service}-{namespace}
    
    Args:
        exporter: Exporter type (e.g., 'kafka', 'redis', 'mysql')
        service: Service name (e.g., 'my-cluster-kafka-bootstrap')
        namespace: Kubernetes namespace (e.g., 'kafka')
        
    Returns:
        Deterministic Helm release name
        
    Examples:
        >>> create_exporter_release_name('kafka', 'my-cluster-kafka-bootstrap', 'kafka')
        'azmon-kafka-exporter-my-cluster-kafka-bootstrap-kafka'
        
        >>> create_exporter_release_name('redis', 'redis', 'redis')
        'azmon-redis-exporter-redis-redis'
    """
    exporter_c = _canonicalize_segment(exporter)
    svc_c = _canonicalize_segment(service)
    ns_c = _canonicalize_segment(namespace)
    
    base = f"azmon-{exporter_c}-exporter-{svc_c}-{ns_c}"
    
    # If within length limit, return as-is
    if len(base) <= MAX_RELEASE_LEN:
        return base
    
    # Need to shorten - use smarter truncation strategy
    service_hash = hashlib.sha256(service.encode()).hexdigest()[:6]  # Shorter hash
    
    # Try to preserve meaningful parts of service name
    # Remove common prefixes/suffixes that might be redundant
    svc_simplified = svc_c
    for pattern in [f'-{exporter_c}', f'{exporter_c}-', '-service', '-svc', '-server']:
        svc_simplified = svc_simplified.replace(pattern, '')
    
    # Calculate space for meaningful service portion
    fixed_parts = f"azmon-{exporter_c}-exporter--{service_hash}-{ns_c}"
    available_space = MAX_RELEASE_LEN - len(fixed_parts)
    
    # Use as much of the simplified service name as possible
    if available_space > 8:
        svc_part = svc_simplified[:available_space]
    else:
        # Fall back to cluster/instance identifier if possible
        parts = svc_c.split('-')
        if len(parts) > 1:
            svc_part = parts[0][:max(4, available_space)]  # Use first meaningful part
        else:
            svc_part = svc_c[:max(4, available_space)]
    
    shortened = f"azmon-{exporter_c}-exporter-{svc_part}-{service_hash}-{ns_c}"
    
    # Final safety truncation if still too long
    return shortened[:MAX_RELEASE_LEN] if len(shortened) > MAX_RELEASE_LEN else shortened

def is_managed_exporter_release(release_name: str) -> bool:
    """
    Check if a Helm release name matches our managed exporter pattern.
    
    Args:
        release_name: Helm release name to check
        
    Returns:
        True if the release name matches our azmon-*-exporter-*-* pattern
    """
    if not release_name:
        return False
    
    # Pattern: azmon-{exporter}-exporter-{service}-{namespace}
    pattern = r"^azmon-[a-z0-9-]+-exporter-[a-z0-9-]+-[a-z0-9-]+$"
    return bool(re.match(pattern, release_name))

def parse_exporter_release_name(release_name: str) -> Dict[str, str]:
    """
    Parse components from a managed exporter release name.
    
    Args:
        release_name: Managed exporter release name
        
    Returns:
        Dictionary with 'exporter', 'service', 'namespace' keys, or empty dict if not parseable
        
    Note:
        For hashed service names, returns the truncated+hashed version, not the original service name.
    """
    if not is_managed_exporter_release(release_name):
        return {}
    
    # Remove azmon- prefix and -exporter suffix, then split
    # azmon-kafka-exporter-my-service-namespace -> kafka-exporter-my-service-namespace
    without_prefix = release_name[6:]  # Remove 'azmon-'
    
    # Find the exporter part (everything before '-exporter-')
    exporter_end = without_prefix.find('-exporter-')
    if exporter_end == -1:
        return {}
    
    exporter = without_prefix[:exporter_end]
    remainder = without_prefix[exporter_end + 10:]  # Skip '-exporter-'
    
    # Split remainder into service and namespace (last segment is namespace)
    parts = remainder.split('-')
    if len(parts) < 2:
        return {}
    
    namespace = parts[-1]
    service = '-'.join(parts[:-1])
    
    return {
        'exporter': exporter,
        'service': service,
        'namespace': namespace
    }

# Common exporter type mappings for workload detection
WORKLOAD_TO_EXPORTER = {
    'kafka': 'kafka',
    'redis': 'redis', 
    'mysql': 'mysqld',
    'postgresql': 'postgres',
    'mongodb': 'mongodb',
    'elasticsearch': 'elasticsearch',
    'rabbitmq': 'rabbitmq',
    'nginx': 'nginx',
    'apache': 'apache',
    'memcached': 'memcached',
    'haproxy': 'haproxy',
}

def get_exporter_name_for_workload(workload_type: str) -> str:
    """
    Get the standard exporter name for a workload type.
    
    Args:
        workload_type: Type of workload (e.g., 'kafka', 'redis', 'my-cluster-kafka-brokers')
        
    Returns:
        Standard exporter name, defaults to detected type or workload_type if not found
    """
    workload_lower = workload_type.lower()
    
    # Direct mapping first
    if workload_lower in WORKLOAD_TO_EXPORTER:
        return WORKLOAD_TO_EXPORTER[workload_lower]
    
    # Try to detect from service name patterns
    for known_type, exporter_name in WORKLOAD_TO_EXPORTER.items():
        if known_type in workload_lower:
            return exporter_name
    
    # Common patterns in service names
    service_patterns = {
        'postgres': 'postgres',
        'mysql': 'mysqld', 
        'redis': 'redis',
        'kafka': 'kafka',
        'elasticsearch': 'elasticsearch',
        'rabbitmq': 'rabbitmq',
        'mongodb': 'mongodb',
        'nginx': 'nginx',
        'apache': 'apache'
    }
    
    for pattern, exporter in service_patterns.items():
        if pattern in workload_lower:
            return exporter
    
    # Fallback to original name
    return workload_lower
