## **1. Preflight Checks and CRD Readiness**

Before deploying, **verify the following:**
- The cluster has the `ServiceMonitor` (and `PodMonitor`) CustomResourceDefinitions (CRDs) installed.
These are required for Azure Managed Prometheus (see [Azure
instructions](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/prometheus-metrics-confi
guration#enable-collection-of-custom-prometheus-metrics)).
    ```sh
    kubectl get crds | grep servicemonitor
    ```
  Expected output should include `servicemonitors.azmonitoring.coreos.com`.

- The Azure Monitor agent is running and has `get/list/watch` RBAC access to `ServiceMonitor` in the
`default` namespace.

---

## **2. Consistent Labeling Across All Resources**

### A. Add a Standard Label to the Deployment

Patch or update your `nginx-deployment` to include the following label (for selector consistency):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  namespace: default
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
        # (volumeMounts added later)
```

---

### B. Enable `/stub_status` in NGINX via ConfigMap

Create a ConfigMap to serve `/stub_status`, restrict access to the exporter’s namespace (ensure CIDR is
correct for your setup):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-status-conf
  namespace: default
data:
  default.conf: |
    server {
        listen 80;
        location / {
            root   /usr/share/nginx/html;
            index  index.html index.htm;
        }
        location /stub_status {
            stub_status;
            allow <EXPORTER_POD_CIDR_OR_IP>;  # e.g., 10.244.0.0/16 or specific exporter Pod IP
            deny all;
        }
    }
```
**Security Note:**
- Do NOT use `allow all`. Only allow your Prometheus exporter’s namespace CIDR or Pod IPs.
- This provides in-NGINX protection for the stub_status endpoint.

---

### C. Mount ConfigMap Into Deployment

Update your Deployment to mount the ConfigMap:

```yaml
      containers:
      - name: nginx
        image: nginx:1.14.2
        volumeMounts:
        - name: nginx-status-conf
          mountPath: /etc/nginx/conf.d
      volumes:
      - name: nginx-status-conf
        configMap:
          name: nginx-status-conf
```
After applying, rollout restart NGINX deployment to activate conf changes.

---

## **3. Expose NGINX via Internal ClusterIP Service**

Create a Service with the **same label (`app: nginx`)**:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
  namespace: default
  labels:
    app: nginx
spec:
  selector:
    app: nginx  # Must match deployment label!
  ports:
    - name: http
      port: 80
      targetPort: 80
      protocol: TCP
  type: ClusterIP
```

---

## **4. (Optional But Recommended) Apply NetworkPolicy**

Restrict traffic to `/stub_status` with a Kubernetes NetworkPolicy as another layer of defense (if your
cluster supports it):

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-prometheus-exporter-nginx
  namespace: default
spec:
  podSelector:
    matchLabels:
      app: nginx
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: azmon-nginx-exporter
    ports:
    - protocol: TCP
      port: 80
  policyTypes:
  - Ingress
```
**Note:** You must label the exporter namespace as follows:
```sh
kubectl label namespace azmon-nginx-exporter name=azmon-nginx-exporter
```
This ensures only Pods in the `azmon-nginx-exporter` namespace can access NGINX on port 80.

---

## **5. Deploy Prometheus NGINX Exporter via Helm**

### A. Create Exporter Namespace

```sh
kubectl create namespace azmon-nginx-exporter
kubectl label namespace azmon-nginx-exporter name=azmon-nginx-exporter
```

### B. Helm Install (with Correct Parameters)

> - The exporter scrapes NGINX via its Service (`nginx-service.default.svc.cluster.local/stub_status`).
> - The ServiceMonitor will be created in **the same namespace as the NGINX Service (i.e., `default`)**
for discoverability by AMA and Azure’s default expectations.

```sh
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install azmon-nginx-exporter \
  prometheus-community/prometheus-nginx-exporter \
  --namespace azmon-nginx-exporter \
  --version 1.1.0 \
  --set nginx.scrapeUri="http://nginx-service.default.svc.cluster.local/stub_status" \
  --set serviceMonitor.enabled=true \
  --set serviceMonitor.namespace="default" \
  --set serviceMonitor.apiVersion="azmonitoring.coreos.com/v1" \
  --set serviceMonitor.labels.prometheus\\.azure\\.com/autoDiscovery="true"
```
- `serviceMonitor.namespace="default"` ensures the ServiceMonitor appears where Azure and Prometheus
expect it (and can discover the Service).
- The exporter will run in its own namespace for isolation.

---

## **6. ServiceMonitor Customization (if Not Using Helm-Created One)**

If creating a ServiceMonitor **manually** or for advanced use-cases:

```yaml
apiVersion: azmonitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: nginx-servicemonitor
  namespace: default
  labels:
    prometheus.azure.com/autoDiscovery: "true"
spec:
  selector:
    matchLabels:
      app: nginx            # Must match Service label
  endpoints:
    - port: http
      path: /stub_status
      interval: 15s
```
**Key Points:**
- Place ServiceMonitor in `default` namespace.
- Match `app: nginx` label so ServiceMonitor discovers the correct Service.
---

## **7. Validation Steps**

### A. Validate stub_status Endpoint

From the exporter pod in the exporter’s namespace:
```sh
kubectl exec -n azmon-nginx-exporter <exporter-pod-name> -- curl -s
http://nginx-service.default.svc.cluster.local/stub_status
```
**Expected output** (example):

```
Active connections: 1
server accepts handled requests
 12 12 12
Reading: 0 Writing: 1 Waiting: 0
```

### B. Validate Exporter Logs

```sh
kubectl logs -n azmon-nginx-exporter <exporter-pod-name>
```
Look for lines indicating successful scraping.

### C. Confirm ServiceMonitor Discovery

```sh
kubectl get servicemonitor -n default
```
Should list a ServiceMonitor in the `default` namespace with correct labels.

### D. Confirm Metrics in Azure

- In Azure Portal → Container Insights/Monitor → Metrics, search for:
    - `nginx_http_connections`
    - `nginx_http_requests_total`
  and other `nginx_` prefixed metrics.

---

## **8. RBAC Review**

Make sure the Azure Monitor agent (`ama-metrics-prometheus`) has permission to list and get
`ServiceMonitor` resources in **default** namespace. Example ClusterRoleBinding:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: ama-prometheus-servicemonitor-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: ama-metrics-reader
subjects:
- kind: ServiceAccount
  name: ama-metrics-prometheus
  namespace: kube-system
```
Adjust `serviceAccount`/`namespace` as per your cluster.

---

## **9. Troubleshooting**

- If no metrics, check:
  - Exporter pod logs.
  - ServiceMonitor and endpoints status (`kubectl describe servicemonitor ...`).
  - Accessibility of `nginx-service`.
  - AMA logs (`kubectl logs -n kube-system -l rsName=ama-metrics-prometheus`).

---

## **References**

- [NGINX Exporter Helm
Chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-nginx-exporter)
- [NGINX stub_status](https://nginx.org/en/docs/http/ngx_http_stub_status_module.html)
- [Azure Managed Prometheus
Setup](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/prometheus-metrics)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

---

## **Concise Step Summary**

1. **Ensure CRDs are present and Azure Monitor agent is properly permissioned.**
2. **Patch workload for `app: nginx` label uniformity.**
3. **Enable and restrict `/stub_status` in NGINX (ConfigMap).**
4. **Mount ConfigMap in the deployment and rollout restart.**
5. **Expose NGINX via ClusterIP Service with matching label.**
6. **(Optional) Restrict access using NetworkPolicy.**
7. **Install exporter Helm chart, setting ServiceMonitor’s namespace to `default`.**
8. **Validate metric ingestion from stub_status to Azure Monitor.**
9. **Troubleshoot as needed.**

---

**Security Reminder:**
Rely on both NGINX allow/deny and Kubernetes NetworkPolicy for `/stub_status` protection. Never expose
to untrusted networks.

**Namespace/Selector Reminder:**
ServiceMonitor **must** be in the `default` namespace to monitor the NGINX Service. Labels must be
consistent (`app: nginx`) across Deployment, Service, and ServiceMonitor.