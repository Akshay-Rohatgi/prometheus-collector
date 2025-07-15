from kubernetes import client, config
from typing import List, Dict, Optional, Any
import rich
from pydantic import BaseModel

# Blacklist for filtering deployments
DEPLOYMENT_BLACKLIST = {
    # Core Kubernetes services
    "coredns", "kube-dns", "etcd", "kube-apiserver", "kube-controller-manager", 
    "kube-proxy", "kube-scheduler", "metrics-server",

    # Azure managed services
    "ama-logs", "ama-metrics", "azure-", "azmon-", "azure-wi-webhook",
    "konnectivity-agent", "eraser-controller", "image-cleaner",

    # Prometheus/monitoring that's already managed
    "prometheus-collector", "prometheus-reference-app", "targetallocator",
    "config-reader",

    # System components
    "cluster-autoscaler", "cluster-proportional-autoscaler",
}

# Namespace blacklist for filtering
NAMESPACE_BLACKLIST = {
    "kube-system", "kube-public", "kube-node-lease", "azure-arc",
    "gatekeeper-system", "calico-system", "tigera-operator"
}

class Workload(BaseModel):
    name: str
    image: str
    namespace: str
    metadata_name: str
    metadata_labels: Dict[str, str]
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

def filter_deployments(deployments: List[Dict]) -> List[Dict]:
    import k8s_tools
    """
    This function is responsible for filtering out irrelevant workloads
    1. It uses a blacklist of known non-OSS workloads that will never be relevant
    2. It deterministically filters out workloads by explicitly checking to see if they are managed by Azure or Microsoft
    3. It uses an LLM filter out workloads that are not relevant to the user, this is only activated if there are an egregious number of workloads remaining
    """
    # these functions should eventually be placed in a separate module
    
    # step 1: blacklist filtering
    deployments = k8s_tools.filter_deployments_by_blacklist(deployments, DEPLOYMENT_BLACKLIST, NAMESPACE_BLACKLIST)

    # step 2: deterministic filtering
    # print(deployments)
    # deployments = self.deterministic_filtering(deployments)

    return deployments

def create_workloads(deployments: List[Dict]) -> List[Workload]:
    """Create workloads directly from deployment data"""
    workloads = []
    for deployment in deployments:
        workload = Workload(
            name=deployment["metadata"]["name"],
            image=deployment["spec"]["template"]["spec"]["containers"][0]["image"],
            namespace=deployment["metadata"]["namespace"],
            metadata_name=deployment["metadata"]["name"],
            metadata_labels=deployment["metadata"]["labels"],
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
    import k8s_tools
    """
    Detect workloads in the Kubernetes cluster.
    This function retrieves all deployments and creates Workload objects.
    """
    namespaces = k8s_tools.get_relevant_namespaces(k8s_client)
    deployments = k8s_tools.get_deployments(k8s_client, namespaces)

    if not deployments:
        rich.print("No deployments found in relevant namespaces.")
        return []

    filtered_deployments = filter_deployments(deployments)

    if not filtered_deployments:
        rich.print("No relevant deployments found.")
        return []

    workloads = create_workloads(filtered_deployments)
    
    return workloads

if __name__ == "__main__":
    import k8s_tools
    k8s_client = K8sClient("/mnt/c/Users/t-arohatgi/.kube/config")

    # grab all deployments in relevant namespaces
    # NOTE: there is much more than just deployments in a cluster (e.g. StatefulSets, ReplicaSets, DaemonSets), this is just a starting point
    namespaces = k8s_tools.get_relevant_namespaces(k8s_client)
    deployments = k8s_tools.get_deployments(k8s_client, namespaces)

    # skip if no namespaces found
    if not deployments:
        rich.print("No deployments found in relevant namespaces.")
        exit(0)

    # filter deployments
    filtered_deployments = filter_deployments(deployments)

    # skip if no relevant deployments found
    if not filtered_deployments:
        rich.print("No relevant deployments found.")
        exit(0)

    # create workloads directly from filtered deployments
    workloads = create_workloads(filtered_deployments)
    
    # save workloads to JSON for persistence
    with open("workloads.json", "w") as f:
        import json
        json.dump([workload.model_dump() for workload in workloads], f, indent=2)

    print("Detected Workloads:")
    for workload in workloads:
        rich.print(f"🔎 Workload: {workload.name} in namespace {workload.namespace}")

