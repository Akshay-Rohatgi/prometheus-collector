from typing import List, Dict
from .client import K8sClient, Workload
from utils import printer
import re

def get_namespaces(k8s_client: K8sClient) -> List[Dict]:
    namespaces = k8s_client.core_api.list_namespace()
    return [namespace.to_dict() for namespace in namespaces.items]

def get_labels_for_namespace(k8s_client: K8sClient, namespace: str) -> Dict[str, str]:
    """Get labels for a specific namespace"""
    namespace_obj = k8s_client.core_api.read_namespace(name=namespace)
    # print(namespace_obj)
    return namespace_obj.metadata.labels if namespace_obj.metadata.labels else {}

def prune_namespaces(k8s_client: K8sClient, namespaces: List[Dict]) -> List[Dict]:
    """
    Prune namespaces that are not relevant for the workload analysis.
    """
    pruned_namespaces = []

    # ignore anything managed by Azure
    for namespace in namespaces:
        labels = get_labels_for_namespace(k8s_client, namespace["metadata"]["name"])
        if labels.get("kubernetes.azure.com/managedby") == "aks":
            printer.out(f"❌ Skipping namespace {namespace['metadata']['name']} due to Azure management")
            continue
        pruned_namespaces.append(namespace)

    return pruned_namespaces

def get_relevant_namespaces(k8s_client: K8sClient) -> List[str]:
    """
    Get a list of relevant namespaces that are not managed by Azure or Microsoft.
    """
    from .filters import NAMESPACE_BLACKLIST
    
    namespaces = get_namespaces(k8s_client)
    pruned_namespaces = prune_namespaces(k8s_client, namespaces)
    
    relevant_namespaces = []
    for namespace in pruned_namespaces:
        namespace_name = namespace["metadata"]["name"]
        if namespace_name not in NAMESPACE_BLACKLIST:
            relevant_namespaces.append(namespace_name)
    
    return relevant_namespaces

def get_deployments(k8s_client: K8sClient, namespaces: List[str]) -> List[Dict]:
    deployments = []
    for namespace in namespaces:
        namespace_deployments = k8s_client.apps_api.list_namespaced_deployment(namespace)
        deployments.extend([deployment.to_dict() for deployment in namespace_deployments.items])
    return deployments

def filter_deployments_by_blacklist(deployments: List[Dict], deployment_blacklist: set, namespace_blacklist: set) -> List[Dict]:
    """
    Filter out deployments that are in the blacklist.
    """
    candidates = []
    
    for deployment in deployments:
        name = deployment["metadata"]["name"].lower()
        namespace = deployment["metadata"]["namespace"].lower()
        
        # skip blacklisted namespaces
        if namespace in namespace_blacklist:
            continue
            
        # skip if name contains any blacklisted terms
        if any(blacklisted in name for blacklisted in deployment_blacklist):
            continue

        candidates.append(deployment)
        
    return candidates

def get_pods_in_namespace(k8s_client: K8sClient, namespace: str) -> List[Dict]:
    """
    Get all pods in a specific namespace.
    """
    pods = k8s_client.core_api.list_namespaced_pod(namespace)
    return [pod.to_dict() for pod in pods.items]

def get_ama_metric_pod_names(k8s_client: K8sClient, namespace: str = "kube-system") -> List[str]:
    """
    Get pod names that are related to Azure Monitor Agent (AMA) metrics.
    """
    # ama metric pods look like: ama-metrics-<10-digit-hex>-<5-digit-hex>
    ama_metric_pod_names = []
    pods = get_pods_in_namespace(k8s_client, namespace)
    for pod in pods:
        # print(pod["metadata"]["name"])
        pod_name = pod["metadata"]["name"]
        # Match pattern: ama-metrics-<10 hex>-<5 hex>
        if re.fullmatch(r"ama-metrics-([0-9]|[a-z]|[A-Z]){10}-([0-9]|[a-z]|[A-Z]){5}", pod_name):
            printer.out(f"✅ Found AMA metric pod: {pod_name}")
            ama_metric_pod_names.append(pod_name)
        else:
            printer.out(f"❌ Skipping pod {pod_name} as it does not match AMA metrics naming convention")

    return ama_metric_pod_names


def get_prometheus_targets_api(k8s_client: K8sClient, pod_name: str, namespace: str = "kube-system", port: int = 9090) -> Dict:
    """
    Alternative approach using the Kubernetes API client directly.

    WARNING: INCOMPLETE - This is a placeholder for the actual implementation.
    """
    try:
        # Use the connect_get_namespaced_pod_proxy method
        pod_name = "ama-metrics-operator-targets-678d8c777-7n9th"
        response = k8s_client.core_api.connect_get_namespaced_pod_proxy(
            name=pod_name + ":" + "8080" +"/targets",
            namespace=namespace,
            path="/",
        )


        # The response should be the targets data
        return response
        
    except Exception as e:
        printer.error(f"Failed to get Prometheus targets via API: {str(e)}")
        return None
