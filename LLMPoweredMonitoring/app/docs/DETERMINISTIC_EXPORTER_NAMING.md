# Deterministic Exporter Naming

## Overview

This module implements deterministic naming for Helm releases used to deploy Prometheus exporters. This enables reliable detection and management of already-monitored workloads by ensuring consistent, predictable release names.

## Naming Convention

**Template**: `azmon-{exporter}-exporter-{service}-{namespace}`

### Examples

| Workload | Service Name | Namespace | Release Name |
|----------|--------------|-----------|--------------|
| Kafka | `my-cluster-kafka-bootstrap` | `kafka` | `azmon-kafka-exporter-my-cluster-kafka-bootstrap-kafka` |
| Redis | `redis` | `redis` | `azmon-redis-exporter-redis-redis` |
| MySQL | `mysql-primary` | `database` | `azmon-mysql-exporter-mysql-primary-database` |

## Implementation

### Core Functions

```python
from ai.utils.exporter_naming import create_exporter_release_name, get_exporter_name_for_workload

# Generate deterministic release name
release_name = create_exporter_release_name('kafka', 'my-service', 'my-namespace')

# Get standard exporter name for workload
exporter = get_exporter_name_for_workload('kafka')  # Returns 'kafka'
exporter = get_exporter_name_for_workload('mysql')  # Returns 'mysqld'
```

### Integration Points

1. **Plan Generation** (`ai/tools.py`): Injects deterministic release name into prompts
2. **Plan Evaluation** (`ai/graphs.py`): Validates plans use correct release names
3. **Already-Monitored Detection**: Can identify existing exporters by release name pattern

## Features

### Canonicalization Rules

- Convert to lowercase
- Replace non-alphanumeric characters (except hyphens) with hyphens
- Collapse consecutive hyphens
- Trim leading/trailing hyphens
- Ensure minimum valid segment length

### Length Handling

- Maximum release name length: 53 characters (Helm/Kubernetes safe)
- For long service names: truncate + SHA256 hash to prevent collisions
- Example: `azmon-mysql-exporter-very-long-se-7a1be40d-production`

### Detection Utilities

```python
from ai.utils.exporter_naming import is_managed_exporter_release, parse_exporter_release_name

# Check if release follows our pattern
is_managed = is_managed_exporter_release('azmon-kafka-exporter-my-svc-kafka')  # True
is_managed = is_managed_exporter_release('random-release-name')  # False

# Parse components from release name  
components = parse_exporter_release_name('azmon-kafka-exporter-my-svc-kafka')
# Returns: {'exporter': 'kafka', 'service': 'my-svc', 'namespace': 'kafka'}
```

## Benefits

1. **Idempotent Monitoring**: Prevent duplicate exporters for same workload
2. **Reliable Detection**: Consistent pattern enables automated discovery
3. **Namespace Isolation**: Include namespace in name prevents collisions
4. **Collision Avoidance**: Hash fallback for very long service names
5. **Future-Proof**: Enables advanced monitoring state management

## Migration Strategy

1. ✅ **Phase 1**: Implement deterministic naming (current)
2. 🔄 **Phase 2**: Add detection to skip already-monitored workloads  
3. 🔄 **Phase 3**: Optional cleanup of legacy non-deterministic releases

## Configuration

### Workload-to-Exporter Mappings

The system includes built-in mappings for common workloads:

```python
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
```

Unknown workload types default to the workload name in lowercase.

## Testing

Run the test suite to validate naming behavior:

```bash
python -c "
from ai.utils.exporter_naming import create_exporter_release_name
assert create_exporter_release_name('kafka', 'my-cluster-kafka-bootstrap', 'kafka') == 'azmon-kafka-exporter-my-cluster-kafka-bootstrap-kafka'
print('✅ Tests passed')
"
```
