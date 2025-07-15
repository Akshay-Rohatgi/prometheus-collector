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