from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from kubernetes import client, config
from printer import printer

# class Workload(BaseModel):
#     name: str
#     image: str
#     namespace: str
#     metadata_name: str
#     metadata_labels: Optional[Dict[str, str]] = None  # Labels might not exist
#     containers: List[Dict[str, Any]]  # Changed from List[Dict[str, List[str]]]
    
#     # Optional fields for future extension
#     workload_type: Optional[str] = "deployment"  # could be "statefulset", "daemonset", etc.
#     is_oss: Optional[bool] = None
#     monitoring_config: Optional[Dict] = None

class Workload(BaseModel):
    '''
    Represents a Kubernetes workload (service).
    '''
    name: str
    namespace: str
    metadata_name: str
    metadata_labels: Optional[Dict[str, str]] = None  # Labels might not exist
    service_type: str # e.g., "ClusterIP", "NodePort", "LoadBalancer"
    service_ports: List[Dict[str, Any]]  # List of ports for the service
    service_annotations: Optional[Dict[str, str]] = None  # Annotations for the service

    # Optional fields for future extension
    # workload_type: Optional[str] = "deployment"  # could be "statefulset", "daemonset", etc.
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

def filter_services(services: List[Dict]) -> List[Dict]:
    from . import tools
    from .filters import DEPLOYMENT_BLACKLIST, NAMESPACE_BLACKLIST
    """
    This function is responsible for filtering out irrelevant services
    1. It uses a blacklist of known non-OSS services that will never be relevant
    2. It deterministically filters out services by explicitly checking to see if they are managed by Azure or Microsoft
    """
    # step 1: blacklist filtering
    services = tools.filter_services_by_blacklist(services, DEPLOYMENT_BLACKLIST, NAMESPACE_BLACKLIST)

    # step 2: deterministic filtering
    # print(services)
    # services = self.deterministic_filtering(services)

    return services

def create_workloads_for_deployments(deployments: List[Dict]) -> List[Workload]:
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

def create_workloads(services: List[Dict]) -> List[Workload]:
    """Create workloads directly from service data"""
    workloads = []
    for service in services:
        metadata = service.get("metadata", {})
        spec = service.get("spec", {})

        ports = []
        for port in spec.get("ports", []):
            port_info = {
                "name": port.get("name"),
                "port": port.get("port"),
                "target_port": port.get("targetPort"),
                "protocol": port.get("protocol", "TCP") 
            }
            ports.append(port_info)

        workload = Workload(
            name=metadata.get("name", ""),
            namespace=metadata.get("namespace", ""),
            metadata_name=metadata.get("name", ""),
            metadata_labels=metadata.get("labels", {}),
            service_type=spec.get("type", "ClusterIP"),
            service_ports=ports,
            service_annotations=metadata.get("annotations"),
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
    # deployments = tools.get_deployments(k8s_client, namespaces)
    services = tools.get_services(k8s_client, namespaces)
    # printer.out(services)

    if not services:
        printer.out("No services found in the cluster.")
        return []

    filtered_services = filter_services(services)

    if not filtered_services:
        printer.out("No relevant services found after filtering.")
        return []

    workloads = create_workloads(filtered_services)
    
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
