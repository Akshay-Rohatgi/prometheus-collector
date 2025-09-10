"""Helm utilities for detecting existing monitoring deployments."""

import subprocess
import json
import time
import shutil
import logging
from typing import List, Dict, Set

# Initialize logger
logger = logging.getLogger(__name__)

# Simple cache with TTL
_CACHE = {"ts": 0, "data": []}
_CACHE_TTL = 5  # Cache for 5 seconds to avoid repeated calls

def list_helm_releases(all_namespaces: bool = True) -> List[Dict]:
    """
    List all Helm releases in the cluster.
    
    Args:
        all_namespaces: If True, list releases from all namespaces
        
    Returns:
        List of release dictionaries with name, namespace, revision, etc.
        Returns empty list if helm is unavailable or command fails.
    """
    # Check cache first
    now = time.time()
    if now - _CACHE["ts"] < _CACHE_TTL and _CACHE["data"]:
        logger.debug("Using cached helm releases")
        return _CACHE["data"]
    
    # Check if helm is available
    if not shutil.which("helm"):
        logger.warning("helm binary not found on PATH", extra={
            'component': 'helm_utils',
            'operation': 'list_helm_releases',
            'error': 'helm_not_found'
        })
        return []
    
    try:
        # Build command
        cmd = ["helm", "list", "--output", "json"]
        if all_namespaces:
            cmd.append("-A")
        
        # Execute with timeout
        proc = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        
        # Parse JSON response
        try:
            data = json.loads(proc.stdout or "[]")
            if isinstance(data, list):
                # Update cache
                _CACHE.update(ts=now, data=data)
                logger.debug(f"Retrieved {len(data)} helm releases", extra={
                    'component': 'helm_utils',
                    'operation': 'list_helm_releases',
                    'releases_count': len(data)
                })
                return data
            else:
                logger.warning("helm list returned non-list data", extra={
                    'component': 'helm_utils',
                    'operation': 'list_helm_releases',
                    'data_type': type(data).__name__
                })
                return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse helm list JSON output: {e}", extra={
                'component': 'helm_utils',
                'operation': 'list_helm_releases',
                'error': 'json_decode_error',
                'stdout': proc.stdout
            })
            return []
            
    except subprocess.TimeoutExpired:
        logger.warning("helm list command timed out after 5s", extra={
            'component': 'helm_utils',
            'operation': 'list_helm_releases',
            'error': 'timeout'
        })
        return []
    except subprocess.CalledProcessError as e:
        logger.warning(f"helm list command failed with exit code {e.returncode}: {e.stderr}", extra={
            'component': 'helm_utils',
            'operation': 'list_helm_releases',
            'error': 'command_failed',
            'exit_code': e.returncode,
            'stderr': e.stderr
        })
        return []
    except Exception as e:
        logger.warning(f"Unexpected error listing helm releases: {e}", extra={
            'component': 'helm_utils',
            'operation': 'list_helm_releases',
            'error': 'unexpected_error'
        })
        return []

def get_release_name_set() -> Set[str]:
    """
    Get a set of all Helm release names in the cluster.
    
    Returns:
        Set of release names. Empty set if helm is unavailable.
    """
    releases = list_helm_releases()
    release_names = {r.get("name", "") for r in releases if r.get("name")}
    
    logger.debug(f"Found {len(release_names)} unique release names", extra={
        'component': 'helm_utils',
        'operation': 'get_release_name_set',
        'unique_releases': len(release_names)
    })
    
    return release_names

def generate_candidate_release_names(workload_name: str, namespace: str) -> Set[str]:
    """
    Generate candidate release names for a workload that might indicate it's already monitored.
    
    Args:
        workload_name: Name of the Kubernetes workload
        namespace: Namespace of the workload
        
    Returns:
        Set of candidate release names to check against existing Helm releases
    """
    candidates = set()
    
    # Base candidate: simple workload-namespace pattern
    base_candidate = f"{workload_name}-{namespace}"
    candidates.add(base_candidate)
    
    # Try to generate deterministic exporter names if the naming utility is available
    try:
        from ai.utils.exporter_naming import create_exporter_release_name, get_exporter_name_for_workload
        
        # Get possible exporter name for this workload
        exporter_name = get_exporter_name_for_workload(workload_name)
        if exporter_name:
            # Generate the deterministic azmon-* pattern
            deterministic_name = create_exporter_release_name(exporter_name, workload_name, namespace)
            candidates.add(deterministic_name)
            
            logger.debug(f"Generated deterministic candidate: {deterministic_name}", extra={
                'component': 'helm_utils',
                'operation': 'generate_candidate_release_names',
                'workload': workload_name,
                'namespace': namespace,
                'exporter': exporter_name,
                'deterministic_name': deterministic_name
            })
            
    except ImportError:
        logger.debug("Exporter naming utility not available, using base candidates only", extra={
            'component': 'helm_utils',
            'operation': 'generate_candidate_release_names',
            'workload': workload_name,
            'namespace': namespace
        })
    except Exception as e:
        logger.warning(f"Failed to generate deterministic candidate name: {e}", extra={
            'component': 'helm_utils',
            'operation': 'generate_candidate_release_names',
            'workload': workload_name,
            'namespace': namespace,
            'error': str(e)
        })
    
    logger.debug(f"Generated {len(candidates)} candidate release names for {workload_name}", extra={
        'component': 'helm_utils',
        'operation': 'generate_candidate_release_names',
        'workload': workload_name,
        'namespace': namespace,
        'candidates_count': len(candidates),
        'candidates': list(candidates)
    })
    
    return candidates

def is_workload_monitored(workload_name: str, namespace: str, release_names: Set[str] = None) -> bool:
    """
    Check if a workload is already being monitored based on Helm release names.
    
    Args:
        workload_name: Name of the Kubernetes workload
        namespace: Namespace of the workload  
        release_names: Optional set of release names to check against. 
                      If None, will fetch current releases.
    
    Returns:
        True if any candidate release name matches an existing Helm release
    """
    if release_names is None:
        release_names = get_release_name_set()
    
    candidates = generate_candidate_release_names(workload_name, namespace)
    
    # Check for matches
    matches = candidates.intersection(release_names)
    
    if matches:
        logger.info(f"Workload {workload_name} appears to be monitored via release(s): {matches}", extra={
            'component': 'helm_utils',
            'operation': 'is_workload_monitored',
            'workload': workload_name,
            'namespace': namespace,
            'is_monitored': True,
            'matching_releases': list(matches)
        })
        return True
    
    logger.debug(f"Workload {workload_name} does not appear to be monitored", extra={
        'component': 'helm_utils',
        'operation': 'is_workload_monitored', 
        'workload': workload_name,
        'namespace': namespace,
        'is_monitored': False,
        'candidates_checked': list(candidates)
    })
    
    return False

def clear_cache():
    """Clear the Helm releases cache. Useful for testing."""
    global _CACHE
    _CACHE = {"ts": 0, "data": []}
    logger.debug("Cleared helm releases cache", extra={
        'component': 'helm_utils',
        'operation': 'clear_cache'
    })
