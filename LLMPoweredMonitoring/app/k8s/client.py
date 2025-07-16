from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from kubernetes import client, config
from utils import printer

class Workload(BaseModel):
    name: str
    image: str
    namespace: str
    metadata_name: str
    metadata_labels: Optional[Dict[str, str]] = None  # Labels might not exist
    containers: List[Dict[str, Any]]  # Changed from List[Dict[str, List[str]]]
    
    # Optional fields for future extension
    workload_type: Optional[str] = "deployment"  # could be "statefulset", "daemonset", etc.
    is_oss: Optional[bool] = None
    monitoring_config: Optional[Dict] = None

class K8sClient:
    def __init__(self, kube_config: str = None):
        if kube_config:
            config.load_kube_config(kube_config)
        else:
            config.load_incluster_config()
    
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()
        self.batch_api = client.BatchV1Api()
        self.custom_objects_api = client.CustomObjectsApi()


def filter_deployments(deployments: List[Dict]) -> List[Dict]:
    from . import tools
    from .filters import DEPLOYMENT_BLACKLIST, NAMESPACE_BLACKLIST
    """
    This function is responsible for filtering out irrelevant workloads
    1. It uses a blacklist of known non-OSS workloads that will never be relevant
    2. It deterministically filters out workloads by explicitly checking to see if they are managed by Azure or Microsoft
    3. It uses an LLM filter out workloads that are not relevant to the user, this is only activated if there are an egregious number of workloads remaining
    """
    # these functions should eventually be placed in a separate module
    
    # step 1: blacklist filtering
    deployments = tools.filter_deployments_by_blacklist(deployments, DEPLOYMENT_BLACKLIST, NAMESPACE_BLACKLIST)

    # step 2: deterministic filtering
    # print(deployments)
    # deployments = self.deterministic_filtering(deployments)

    return deployments

def create_workloads(deployments: List[Dict]) -> List[Workload]:
    """Create workloads directly from deployment data"""
    workloads = []
    for deployment in deployments:

        # handle case where labels might not exist
        labels = deployment.get("metadata", {}).get("labels")
        workload = Workload(
            name=deployment["metadata"]["name"],
            image=deployment["spec"]["template"]["spec"]["containers"][0]["image"],
            namespace=deployment["metadata"]["namespace"],
            metadata_name=deployment["metadata"]["name"],
            metadata_labels=labels,  # Now handles None case
            containers=[
                {
                    "name": container["name"],
                    "args": container.get("args"),  # Remove default [] since it can be None
                    "env": container.get("env")     # Remove default [] since it can be None
                }
                for container in deployment["spec"]["template"]["spec"]["containers"]
            ]
        )
        workloads.append(workload)
    return workloads


def detect_workloads(k8s_client: K8sClient) -> List[Workload]:
    from . import tools
    """
    Detect workloads in the Kubernetes cluster.
    This function retrieves all deployments and creates Workload objects.
    """
    namespaces = tools.get_relevant_namespaces(k8s_client)
    deployments = tools.get_deployments(k8s_client, namespaces)

    if not deployments:
        printer.info("No deployments found in relevant namespaces.")
        return []

    filtered_deployments = filter_deployments(deployments)

    if not filtered_deployments:
        printer.info("No relevant deployments found after filtering.")
        return []

    workloads = create_workloads(filtered_deployments)
    
    return workloads

def verify_workloads(k8s_client: K8sClient, workloads: List[Workload]):
    from . import tools
    printer.out(tools.get_ama_metric_pod_names(k8s_client))
    for pod_name in tools.get_ama_metric_pod_names(k8s_client):
        printer.out(tools.get_prometheus_targets_api(k8s_client, pod_name))

if __name__ == "__main__":
    # Example usage
    k8s_client = K8sClient("/mnt/c/Users/t-arohatgi/.kube/config")
    workloads = detect_workloads(k8s_client)
    printer.out(workloads)
