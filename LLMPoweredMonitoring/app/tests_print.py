import rich
# rich.print("""
# This improved monitoring plan for your nginx-deployment solves all reviewer feedback for
# production-ready Prometheus/Grafana monitoring. It includes:\n\n- Accurate, copy/paste-friendly debugging and log commands\n- Helm
# install for kube-prometheus-stack with explicit ServiceMonitor selectors\n- Sidecar deployment YAML for nginx-prometheus-exporter
# and configuration steps for nginx stub_status\n- Full RBAC and NetworkPolicy YAML for secure metric scraping\n- Service and
# ServiceMonitor pointing at the correct metric endpoint\n- A sample Prometheus alert for high nginx 5xx error rates\n- Instructions
# for importing a pre-built Grafana dashboard\n- All commands avoid placeholders and clarify cleanup\n\nWith these steps, you'll get
# robust, secure, and actionable nginx metrics and alerting in your Kubernetes cluster.",
#             'debugging_statements': '# Debugging Statements\n\n## 1. Check Deployment Status (Direct Pod Name Retrieval)\nkubectl
# -n default get pods -l app=nginx-deployment -o name\nkubectl -n default get deployment nginx-deployment\nkubectl -n default
# describe deployment nginx-deployment\n\n## 2. Inspect Pod Logs\nPOD=$(kubectl -n default get pods -l app=nginx-deployment -o
# jsonpath="{.items[0].metadata.name}")\nkubectl -n default logs $POD --tail=100\n\n## 3. Verify Pod Health and NGINX\nkubectl -n
# default get events --sort-by=.metadata.creationTimestamp\nkubectl -n default exec $POD -- nginx -t\nkubectl -n default exec $POD --
# curl -I http://localhost:80/\n\n## 4. Prometheus Target and Metrics Scrape Check\n# 1. Forward Prometheus UI to local:\nkubectl -n
# monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090\n# 2. Open Prometheus UI http://localhost:9090 and
# check \'Status > Targets\'.\n\n## 5. Grafana Access and Dashboard Import\nkubectl -n monitoring get svc\n# Find the
# \'monitoring-grafana\' service and port-forward:\nkubectl -n monitoring port-forward svc/monitoring-grafana 3000:80\n# Access
# Grafana at http://localhost:3000 (default creds: admin/prom-operator) and import dashboard ID 2949 (NGINX) for quick start.\n\n\n',
#             'kubectl_commands': '# kubectl Commands\n\n## 1. Add Labels for Monitoring\nkubectl -n default label deployment
# nginx-deployment app=nginx-deployment metrics=enabled\n\n## 2. Patch NGINX Deployment with Exporter Sidecar\ntemplate=$(cat <<EOF\n
# - name: nginx-exporter\n        image: nginx/nginx-prometheus-exporter:1.1.0\n        args:\n          -
# \'-nginx.scrape-uri=http://localhost:8080/stub_status\'\n        ports:\n        - containerPort: 9113\n          name:
# metrics\nEOF\n)\nkubectl -n default patch deployment nginx-deployment --type=\'json\' -p="[\n
# {\\"op\\":\\"add\\",\\"path\\":\\"/spec/template/spec/containers/-\\",\\"value\\":$template}\n]"\n\n## 3. Patch NGINX config for
# stub_status (inplace, for demo - real configs may differ)\nkubectl -n default exec $POD -- sh -c \'echo -e "\\nserver {\\n
# listen 8080;\\n    location /stub_status {\\n        stub_status;\\n        allow 127.0.0.1;\\n        deny all;\\n    }\\n}" >>
# /etc/nginx/conf.d/stub_status.conf && nginx -s reload\'\n\n## 4. Create Service to Expose Exporter Metrics Endpoint
# (ClusterIP)\ncat <<EOF | kubectl apply -f -\napiVersion: v1\nkind: Service\nmetadata:\n  name: nginx-metrics-svc\n  namespace:
# default\n  labels:\n    app: nginx-deployment\n    metrics: enabled\nspec:\n  type: ClusterIP\n  selector:\n    app:
# nginx-deployment\n  ports:\n    - protocol: TCP\n      port: 9113\n      targetPort: 9113\n      name: metrics\nEOF\n\n## 5. Create
# ServiceMonitor For Exporter\ncat <<EOF | kubectl apply -f -\napiVersion: monitoring.coreos.com/v1\nkind:
# ServiceMonitor\nmetadata:\n  name: nginx-metrics-servicemonitor\n  namespace: default\nspec:\n  selector:\n    matchLabels:\n
# app: nginx-deployment\n      metrics: enabled\n  endpoints:\n    - port: metrics\n      path: /metrics\n      interval:
# 30s\nEOF\n\n## 6. RBAC - Allow Prometheus to scrape metrics from default namespace\ncat <<EOF | kubectl apply -f -\napiVersion:
# rbac.authorization.k8s.io/v1\nkind: Role\nmetadata:\n  name: prometheus-scrape\n  namespace: default\nrules:\n- apiGroups: [\'\']\n
# resources: [\'endpoints\', \'services\', \'pods\']\n  verbs: [\'get\', \'list\', \'watch\']\n---\napiVersion:
# rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata:\n  name: prometheus-scrape-binding\n  namespace: default\nroleRef:\n
# apiGroup: rbac.authorization.k8s.io\n  kind: Role\n  name: prometheus-scrape\nsubjects:\n- kind: ServiceAccount\n  name:
# monitoring-kube-prometheus-prometheus\n  namespace: monitoring\nEOF\n\n## 7. NetworkPolicy Restricting Metrics Scrape (allow only
# from Prometheus pods)\ncat <<EOF | kubectl apply -f -\napiVersion: networking.k8s.io/v1\nkind: NetworkPolicy\nmetadata:\n  name:
# allow-prometheus-scrape\n  namespace: default\nspec:\n  podSelector:\n    matchLabels:\n      app: nginx-deployment\n
# policyTypes:\n    - Ingress\n  ingress:\n    - from:\n        - namespaceSelector:\n            matchLabels:\n              name:
# monitoring\n      ports:\n        - protocol: TCP\n          port: 9113\nEOF\n\n## 8. Create Example Alert Rule (PrometheusRule)
# for NGINX Exporter\ncat <<EOF | kubectl apply -f -\napiVersion: monitoring.coreos.com/v1\nkind: PrometheusRule\nmetadata:\n  name:
# nginx-high-5xx-errors\n  namespace: default\nspec:\n  groups:\n  - name: nginx.rules\n    rules:\n    - alert:
# NginxHigh5xxErrorRate\n      expr: rate(nginx_http_requests_total{status=~"5.."}[5m]) > 0.01\n      for: 2m\n      labels:\n
# severity: warning\n      annotations:\n        summary: High rate of 5xx errors on nginx\n        description: "Nginx is serving
# more than 1% 5xx error codes (>1/100 request) in the last 5 minutes."\nEOF\n\n## 9. Cleanup Resources\nhelm uninstall monitoring
# --namespace monitoring || true\nkubectl -n default delete svc nginx-metrics-svc || true\nkubectl -n default delete servicemonitor
# nginx-metrics-servicemonitor || true\nkubectl -n default delete prometheusrule nginx-high-5xx-errors || true\nkubectl -n default
# delete role prometheus-scrape || true\nkubectl -n default delete rolebinding prometheus-scrape-binding || true\nkubectl -n default
# delete networkpolicy allow-prometheus-scrape || true\nkubectl -n default label deployment nginx-deployment app- metrics-\n\n',
#             'helm_commands': "# Helm Commands\n\n## 1. Add Helm Repositories\nhelm repo add prometheus-community
# https://prometheus-community.github.io/helm-charts\nhelm repo update\n\n## 2. Install kube-prometheus-stack in 'monitoring'
# namespace\nhelm install monitoring prometheus-community/kube-prometheus-stack \\\n  --namespace monitoring --create-namespace \\\n
# --set prometheus.serviceMonitorSelectorNilUsesHelmValues=false \\\n  --set prometheus.serviceMonitorSelector.app=nginx-deployment
# \\\n  --set prometheus.serviceMonitorSelector.metrics=enabled\n\n# For completeness, the default config will watch ServiceMonitors
# in any namespace; these options ensure non-default scoping if desired.\n\n## 3. (Optional) Upgrade/rollback\nhelm upgrade
# monitoring prometheus-community/kube-prometheus-stack --namespace monitoring\nhelm rollback monitoring <REVISION> --namespace
# monitoring\n\n## 4. (Optional) Install Grafana dashboards from the Grafana.com library\n# Inside Grafana (http://localhost:3000) go
# to Dashboards > Import > enter ID 2949 for NGINX metrics. Adjust for your exporter setup.\n\n",
#             'other_instructions': "# Other Instructions\n\n## 1. NGINX Exporter Sidecar Configuration\n- The exporter is injected
# as a sidecar in the deployment. Ensure your NGINX config supports stub_status on localhost:8080.\n- For demo environments, use the
# patch example above; for production, update your Deployment YAML directly.\n- Example stub_status snippet (add to nginx.conf):\n
# server {\n      listen 8080;\n      location /stub_status {\n          stub_status;\n          allow 127.0.0.1;\n          deny
# all;\n      }\n  }\n\n## 2. Network Security\n- The metrics Service should be ClusterIP (default) and the NetworkPolicy will limit
# ingress to Prometheus only from the monitoring namespace, mitigating lateral movement.\n\n## 3. RBAC\n- RBAC manifests are provided
# above. You may need to adjust the service account name depending on your Helm values/configuration.\n\n## 4. Grafana Dashboard
# Setup\n- The kube-prometheus-stack installs Grafana with default credentials (admin/prom-operator). Import dashboard ID 2949 for
# NGINX from https://grafana.com/grafana/dashboards/2949 if you are using the official exporter.\n- Edit or create custom dashboards
# as necessary (refer to the metrics exposed by the nginx-prometheus-exporter).\n\n## 5. PrometheusRule/Alerting\n- The
# PrometheusRule example above generates a warning if 5xx errors exceed 1%. Adapt alert rules as required by your team's SLOs.\n\n##
# 6. Scrape Validation\n- Always verify new ServiceMonitors by checking the Prometheus UI (http://localhost:9090), ensuring targets
# are discovered and healthy.\n- Check Grafana dashboards for live metrics.\n\n## 7. Placeholder Elimination\n- All commands avoid
# <angle brackets>. Where necessary, use $POD shell variable assignments or precise names for direct copy-paste.\n\n## 8. Secret
# Management\n- If you run NGINX in front of protected content or expose exporter endpoints to external clients, add basic auth or
# Kubernetes secrets accordingly (not required for basic internal metrics scraping).\n\n## 9. Cleanup Clarification\n- For cleanup,
# use the provided label removal command that clears both 'app' and 'metrics' labels.\n- Check for remaining resources using e.g.
# kubectl get all -n default -l app=nginx-deployment.\n\n## 10. Troubleshooting Steps\n- Use kubectl describe and logs output for
# detailed failure analysis.\n- For ServiceMonitor issues, inspect Prometheus service discovery logs from the Prometheus pod.\n- Use
# curl from a Prometheus pod (kubectl exec) to verify you can reach the /metrics endpoint directly.\n\n
#            """)

# rich.print("""'## Monitoring Deployment Plan for NGINX Application in Kubernetes using Prometheus\n\nThis document
# outlines a comprehensive monitoring deployment plan for an NGINX application deployed in Kubernetes utilizing Prometheus for
# monitoring.\n\n## Debugging Statements\n- **Check Deployment Status:**   \n  ```bash  \n  kubectl get deployments -n default  \n
# kubectl describe deployment nginx-deployment -n default  \n  ```  \n- **Inspect Pod Logs:**   \n  ```bash  \n  kubectl logs -l
# app=nginx -n default  \n  ```  \n- **Health Check Verifications:**   \n  - Check Pods Status:  \n  ```bash  \n  kubectl get pods -n
# default  \n  ```  \n  - Check Services:  \n  ```bash  \n  kubectl get svc -n default  \n  ```  \n  - Check Prometheus Targets:  \n
# ```bash  \n  curl http://<prometheus-ip>:9090/api/v1/targets  \n  ```  \n\n## kubectl Commands\n- **Create Core Monitoring
# Resources:**  \n  - Create a ServiceMonitor for Prometheus:  \n  ```bash  \n  cat <<EOF | kubectl apply -f -  \n  apiVersion:
# monitoring.coreos.com/v1  \n  kind: ServiceMonitor  \n  metadata:  \n    name: nginx-servicemonitor  \n    namespace: default  \n
# spec:  \n    selector:  \n      matchLabels:  \n        app: nginx  \n    endpoints:  \n      - port: http  \n        path:
# /metrics  \n        interval: 30s  \n    namespaceSelector:  \n      matchNames:  \n        - default  \n  EOF  \n  ```  \n-
# **Configuration Deployments:**  \n  ```bash  \n  kubectl apply -f nginx-deployment.yaml  \n  ```  \n- **Service and Ingress
# Setup:**  \n  - Create a ClusterIP service:  \n  ```bash  \n  kubectl expose deployment nginx-deployment --port=80 --target-port=80
# --name=nginx-service --type=ClusterIP -n default  \n  ```  \n  - Optional Ingress Configuration (Make sure you have a valid ingress
# controller):  \n  ```bash  \n  kubectl apply -f nginx-ingress.yaml  \n  ```  \n\n## Helm Commands\n- **Install Prometheus using
# Helm:**  \n  ```bash  \n  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts  \n  helm repo
# update  \n  helm install prometheus prometheus-community/prometheus  \n  ```  \n- **Values Configuration for Prometheus:**  \n
# Modify the values file for ServiceMonitor configurations if needed:  \n  ```yaml  \n  serviceMonitors:  \n    - name:
# nginx-servicemonitor  \n      selector:  \n        matchLabels:  \n          app: nginx  \n      endpoints:  \n        - port: http
# \n          path: /metrics  \n  ```  \n- **Upgrade/Rollback Procedures:**  \n  ```bash  \n  helm upgrade prometheus
# prometheus-community/prometheus  \n  # Rollback to previous revision  \n  helm rollback prometheus  \n  ```  \n\n## Other
# Instructions\n- **Configuration File Modifications:**  \n  Ensure the NGINX configuration exposes metrics on port 80 or set up an
# NGINX exporter. Example NGINX configuration for metrics:  \n  ```nginx  \n  location /metrics {  \n      stub_status on;  \n
# allow 127.0.0.1;  \n      deny all;  \n  }  \n  ```  \n- **Troubleshooting Steps:**  \n  If monitoring is not functioning
# correctly, check:  \n  - Prometheus targets at its UI: (http://<prometheus-ip>:9090/targets)  \n  - Logs of Prometheus for errors:
# \n  ```bash  \n  kubectl logs -l app=prometheus -n default  \n  ```  \n- **Monitoring Security Best Practices:**  \n  - Ensure that
# your Prometheus and NGINX configurations do not expose sensitive information.  \n  - Limit access to Prometheus and the NGINX
# metrics endpoint to specific IPs or authenticate access if needed.\n  \n## Cleanup Instructions\n- **Resource Cleanup:**  \n  If
# needed, clean up resources after testing:  \n  ```bash  \n  kubectl delete servicemonitor nginx-servicemonitor -n default  \n
# kubectl delete deployment nginx-deployment -n default  \n  kubectl delete svc nginx-service -n default  \n  helm uninstall
# prometheus  \n  ```  \n\n- **Ensure Complete Cleanup:**  \n  Check for leftover resources:  \n  ```bash  \n  kubectl get all -n
# default  \n  ```  \n  to verify that no unwanted resources remain.
#            """)


from rich.console import Console
from rich.markdown import Markdown

console = Console()
# console.print(Markdown("""# Monitoring Deployment Plan for `nginx-deployment`
# (nginx:1.14.2)\n\nThis monitoring plan describes how to instrument the `nginx-deployment` workload in
# the `default` namespace with Azure Managed Prometheus using the [prometheus-nginx-exporter Helm
# chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-nginx-exporter).
# \n\n---\n\n## 1. Deploy Prometheus NGINX Exporter\n\n### 1.1. Determine NGINX Status Endpoint\n\nBy
# default, the [nginx-prometheus-exporter](https://github.com/nginxinc/nginx-prometheus-exporter) scrapes
# NGINX metrics from a [stub_status](http://nginx.org/en/docs/http/ngx_http_stub_status_module.html)
# endpoint.\n**Before deploying the exporter, ensure you have configured an NGINX stub_status endpoint in
# your nginx Deployment.**\n\nAdd the following to your nginx.conf to expose `/status` for monitoring
# (adjust IPs as needed for your cluster security):\n\n```nginx\nserver {\n    listen 8080;\n    location
# /status {\n        stub_status;\n        allow 127.0.0.1;         # Update with exporter pod IP range
# if needed\n        deny all;\n    }\n}\n```\n**WARNING:** The nginx exporter must be able to access
# this endpoint. For security, restrict it to the namespace or use a dedicated Service.\n\n### 1.2.
# Install the nginx-prometheus-exporter\n\n**Parameters:**\n- `nginx.status.endpoint` is the URL to the
# `/status` endpoint exposed by your NGINX deployment.\n- `serviceMonitor.enabled=true` enables Azure
# Managed Prometheus to scrape exporter metrics.\n-
# `serviceMonitor.apiVersion=azmonitoring.coreos.com/v1` ensures compatibility.\n\n**Helm
# Command:**\nReplace `<NGINX_STATUS_ENDPOINT>` with the accessible endpoint URL (e.g.,
# `http://nginx-deployment.default.svc.cluster.local:8080/status`):\n\n```shell\nhelm repo add
# prometheus-community https://prometheus-community.github.io/helm-charts\nhelm repo update\n\nhelm
# install azmon-nginx-exporter \\\n     --namespace default \\\n     --version 0.2.1 \\\n
# prometheus-community/prometheus-nginx-exporter \\\n     --set
# nginx.status.endpoint="http://nginx-deployment.default.svc.cluster.local:8080/status" \\\n     --set
# serviceMonitor.enabled=true \\\n     --set
# serviceMonitor.apiVersion=azmonitoring.coreos.com/v1\n```\n\n> **Note:**  \n> - If `nginx-deployment`
# exposes the status endpoint through a different port or path, adjust the `nginx.status.endpoint`
# accordingly.\n> - If running multiple nginx replicas, ensure the exporter can scrape all pods, or
# consider deploying one exporter as a DaemonSet/Sidecar per instance.\n\n---\n\n## 2. Service Monitor
# (Validation)\n\nThe above Helm chart will automatically create a ServiceMonitor resource named
# `azmon-nginx-exporter`, pre-configured for Azure Managed Prometheus
# (`apiVersion=azmonitoring.coreos.com/v1`). No manual creation is required.\n\n_You can validate success
# with:_\n\n```shell\nkubectl get servicemonitor azmon-nginx-exporter -n default -o
# yaml\n```\n\n---\n\n## 3. Validation and Troubleshooting\n\n- Ensure that the nginx-exporter pod starts
# without errors and that the ServiceMonitor is present.\n- Check metrics endpoint (port 9113 by default)
# and verify Azure Managed Prometheus is scraping it.\n- Confirm metrics appear in Azure Monitor\'s
# "Metrics" section by searching for `nginx_` metric prefixes.\n\n---\n\n## 4. References\n\n-
# [Prometheus NGINX Exporter Helm
# Chart](https://github.com/prometheus-community/helm-charts/tree/main/charts/prometheus-nginx-exporter)\
# n- [Prometheus NGINX Exporter Documentation](https://github.com/nginxinc/nginx-prometheus-exporter)\n-
# [Azure Managed Prometheus
# Documentation](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/prometheus-metrics)\n\n
# ---\n"""))


# console.print(Markdown("""# Monitoring Deployment Plan for `my-cluster-entity-operator`
# (Strimzi Entity Operator)\n\nThis plan enables Prometheus monitoring for the Strimzi Entity Operator
# ("my-cluster-entity-operator") deployed in the `kafka` namespace. Strimzi components support Prometheus
# metrics natively, using `/metrics` endpoints on both the Topic Operator and User Operator containers.
# Instrumentation is achieved using a Prometheus PodMonitor configured for Azure Managed
# Prometheus.\n\n---\n\n## 1. Verify Entity Operator Metrics Endpoints\n\nThe Strimzi Entity Operator
# exposes Prometheus-formatted metrics by default on the following containers:\n\n- **topic-operator**:
# Exposes on port `9404` at `/metrics`\n- **user-operator**: Exposes on port `8080` at `/metrics`\n\n>
# **Note:** Confirm the above default ports (9404 for Topic Operator and 8080 for User Operator) in your
# deployment manifests. If custom ports are configured, adjust accordingly in the next
# steps.\n\n---\n\n## 2. Create a PodMonitor for Entity Operator\n\nAzure Managed Prometheus relies on
# `PodMonitor` custom resources (CRs) to scrape metrics exposed on pod endpoints.\n\n1. Save the
# following YAML as `entity-operator-podmonitor.yaml`.\n2. Apply to the `kafka`
# namespace.\n\n```yaml\napiVersion: azmonitoring.coreos.com/v1\nkind: PodMonitor\nmetadata:\n  name:
# my-cluster-entity-operator\n  namespace: kafka\n  labels:\n    app.kubernetes.io/instance: my-cluster\n
# app.kubernetes.io/name: entity-operator\n    monitor: prometheus\nspec:\n  selector:\n
# matchLabels:\n      app.kubernetes.io/instance: my-cluster\n      app.kubernetes.io/name:
# entity-operator\n  namespaceSelector:\n    matchNames:\n      - kafka\n  podMetricsEndpoints:\n    -
# port: http\n      path: /metrics\n      interval: 30s\n      scheme: http\n      relabelings:\n
# - sourceLabels: [__meta_kubernetes_pod_container_name]\n          regex: topic-operator\n
# action: keep\n    - port: http\n      path: /metrics\n      interval: 30s\n      scheme: http\n
# relabelings:\n        - sourceLabels: [__meta_kubernetes_pod_container_name]\n          regex:
# user-operator\n          action: keep\n```\n\n> **IMPORTANT:**\n> - Replace the `port: http` with the
# actual port name or number as defined in your entity operator pod spec (e.g., `port: 9404` for Topic
# Operator and `port: 8080` for User Operator) if port name mapping is not present.\n> - The above
# PodMonitor targets both containers. If you need to split metrics (due to port names/numbers), use
# multiple `podMetricsEndpoints` entries with appropriate `port` fields.\n\n### Example (When Port
# Numbers Are Used Instead of Names)\n```yaml\n    - port: 9404  # For topic-operator\n    ...\n    -
# port: 8080  # For user-operator\n```\n\n---\n\n## 3. Apply the PodMonitor\n\nRun the following command
# to deploy the PodMonitor:\n\n```bash\nkubectl apply -f
# entity-operator-podmonitor.yaml\n```\n\n---\n\n## 4. (Optional) Validate Pod and Endpoint
# Labels\n\nEnsure that the deployed entity operator pods have the following labels:\n\n-
# `app.kubernetes.io/instance: my-cluster`\n- `app.kubernetes.io/name: entity-operator`\n\nIf your
# deployment uses different labels, update the `spec.selector.matchLabels` section in the PodMonitor
# accordingly.\n\nTo check pod labels:\n\n```bash\nkubectl get pods -n kafka -l
# app.kubernetes.io/name=entity-operator --show-labels\n```\n\n---\n\n## 5. (Optional) Validate Metrics
# Endpoint Exposure\n\nTo verify that the metrics endpoints are accessible:\n\n```bash\nkubectl
# port-forward <entity-operator-pod> 9404:9404 -n kafka\ncurl http://localhost:9404/metrics\n\nkubectl
# port-forward <entity-operator-pod> 8080:8080 -n kafka\ncurl
# http://localhost:8080/metrics\n```\n\nRepeat for both containers as appropriate (topic-operator and
# user-operator).\n\n---\n\n## 6. No Additional Exporters Needed\n\n**NOTE:**  \nThe Strimzi Entity
# Operator (topic/user operators) natively exposes Prometheus metrics, so no separate Prometheus
# exporters or sidecars are required.\n\n---\n\n## 7. Validate Monitoring\n\nOnce the PodMonitor is
# active, check Azure Managed Prometheus for incoming metrics from your entity operator pods, such as:\n-
# `strimzi_resource_events_total`\n- `strimzi_reconciliations_duration_seconds`\n-
# `strimzi_reconciliations_failed_total`\n- `strimzi_topic_operator_*`\n-
# `strimzi_user_operator_*`\n\n---\n\n## 8. Troubleshooting\n\n- Ensure the `PodMonitor` apiVersion is
# `azmonitoring.coreos.com/v1`.\n- Ensure the Azure Managed Prometheus scraper has permission to watch
# `PodMonitor` resources in the `kafka` namespace.\n- Confirm the `PodMonitor` label selectors match your
# pods’ labels exactly.\n- Confirm metrics endpoints are open (no network or RBAC blocks).\n\n---\n\n##
# References\n\n- [Strimzi Monitoring
# Documentation](https://strimzi.io/docs/operators/latest/configuring.html#con-metrics-str)\n-
# [Prometheus PodMonitor
# Docs](https://github.com/prometheus-operator/prometheus-operator/blob/main/Documentation/api.md#podmoni
# tor)\n- [Azure Managed Prometheus
# Integration](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/prometheus-metrics)\n\n--
# -\n"""))
# console.print(Markdown("""### **Analysis**\n\n#### **hello-world**\n- **Signals**:\n  - **Primary Signal**:
# Labels point to RabbitMQ (`app.kubernetes.io/component=\'rabbitmq\'`).\n  - **Secondary Signal**:
# Namespace is `default`, which is neutral.\n  - **Strong Signal**: Ports 5672 (AMQP), 15672 (management
# UI), and 15692 (Prometheus metrics) are strongly associated with RabbitMQ.\n  - **Annotations**:
# None.\n- **Exclusion**: This service represents a RabbitMQ core workload based on ports and labels.
# HIGH confidence.\n\n#### **hello-world-nodes**\n- **Signals**:\n  - **Primary Signal**: Labels suggest
# RabbitMQ (`app.kubernetes.io/component=\'rabbitmq\'`).\n  - **Strong Signal**: This service provides
# cluster internals like EPMD and Cluster RPC (ports 4369 and 25672)—indicative of RabbitMQ node
# management.\n- **Exclusion**: RabbitMQ node services are considered support infrastructure. NOT core.
# EXCLUDE.\n\n#### **investibots-service**\n- **Signals**:\n  - **Primary Signal**: Name does not match
# typical OSS services.\n  - **Labels**: None (no indication of OSS).\n  - **Ports**: HTTP port 80,
# generic usage.\n  - **Annotations**: Represents a custom application.\n- **Exclusion**: Custom/private
# workload without OSS lineage. EXCLUDE.\n\n#### **kubernetes**\n- **Signals**:\n  - **Primary Signal**:
# Name explicitly refers to the Kubernetes API server.\n  - **Labels**: Indicates "kubernetes"
# component.\n- **Exclusion**: This is a system-level Kubernetes component, not a first-class OSS
# application workload. EXCLUDE.\n\n#### **nginx-project**\n- **Signals**:\n  - **Primary Signal**: Name
# and port strongly indicate Nginx (an OSS web server/proxy).\n  - **Secondary Signal**: Namespace is
# `default`, neutral.\n  - **Annotations**: Matches LoadBalancer configuration with a selector targeting
# Nginx.\n- **Exclusion**: Clearly an Nginx core service and suitable for monitoring. HIGH
# confidence.\n\n#### **prometheus-reference-service**\n- **Signals**:\n  - **Primary Signal**: Name
# references Prometheus (but does not appear to be the core Prometheus server).\n  - **Ports**: Custom
# ports (2112, 2113, 2114) do not match Prometheus default port (9090).\n  - **Labels**: Suggests this
# is simply used alongside Prometheus or for custom app metrics.\n- **Exclusion**: Not the core
# Prometheus service, but a custom application. EXCLUDE.\n\n####
# **rabbitmq-rabbitmq-messaging-topology-operator-webhook**\n- **Signals**:\n  - **Primary Signal**:
# Name indicates a webhook for the RabbitMQ messaging topology operator.\n  - **Labels**: Helm-managed
# RabbitMQ operator component.\n  - **Ports**: Port 443 for HTTPS does not represent RabbitMQ core
# services.\n- **Exclusion**: Service belongs to the RabbitMQ operator infrastructure. NOT core.
# EXCLUDE.\n\n#### **my-cluster-kafka-bootstrap**\n- **Signals**:\n  - **Primary Signal**: Name
# explicitly references Kafka (`my-cluster-kafka-bootstrap`).\n  - **Namespace**: Dedicated Kafka
# namespace (`kafka`), strongly positive.\n  - **Labels**: Managed by Strimzi operator, relevant for
# Kafka.\n  - **Ports**: 9092 (Kafka plaintext client), 9093 (TLS Kafka client)—canonical Kafka ports.\n
# - **Annotations**: Indicates Kafka discovery protocol.\n- **Exclusion**: Represents
# support/bootstrapping service for the Kafka cluster. NOT core. EXCLUDE.\n\n####
# **my-cluster-kafka-brokers**\n- **Signals**:\n  - **Primary Signal**: Name references Kafka core
# brokers (`my-cluster-kafka-brokers`).\n  - **Namespace**: Dedicated Kafka namespace (`kafka`),
# strongly positive.\n  - **Labels**: Managed by Strimzi operator, relevant for Kafka.\n  - **Ports**:
# Ports (9092, 9093) reflect Kafka\'s broker services.\n  - **Annotations**: None provided.\n-
# **Inclusion**: Represents core Kafka broker service and suitable for monitoring. HIGH
# confidence.\n\n---\n\n### **Detected OSS Workloads**\nUsing the `add_oss_workload` tool where
# applicable:\n\n1. **hello-world**: RabbitMQ core service  \n2. **nginx-project**: Nginx core service
# \n3. **my-cluster-kafka-brokers**: Kafka core brokers"""))
console.print(Markdown("""### **Analysis of "hello-world"**
1. **SERVICE NAME ANALYSIS**:
   - The name "hello-world" is generic and does not represent a well-known OSS project. However, the
labels indicate its connection to RabbitMQ (`'app.kubernetes.io/component': 'rabbitmq'`), which is a
widely used OSS message broker.

2. **NAMESPACE ANALYSIS**:
   - "hello-world" is in the default namespace, which is neutral but does not detract from its
suitability.

3. **LABELS AND ANNOTATIONS ANALYSIS**:
   - Labels clearly indicate it is part of RabbitMQ, a major OSS project
(`'app.kubernetes.io/part-of': 'rabbitmq'`).

4. **PORT AND PROTOCOL ANALYSIS**:
   - Prominent RabbitMQ ports are present:
     - **5672** (AMQP)
     - **15672** (Management UI)
     - **15692** (Prometheus metrics).
   - This strongly indicates it is a RabbitMQ core service.

5. **SELECTOR ANALYSIS**:
   - Labels reinforce its role as RabbitMQ.

**Decision**: High confidence that this is a core RabbitMQ service.
✅ **Add workload**: "hello-world"

---

### **Analysis of "hello-world-nodes"**
1. **SERVICE NAME ANALYSIS**:
   - Name suggests supporting RabbitMQ nodes functionality rather than the core RabbitMQ service.

2. **NAMESPACE ANALYSIS**:
   - Default namespace is neutral.

3. **LABELS AND ANNOTATIONS ANALYSIS**:
   - Labels indicate association with RabbitMQ but suggest node-level functionality rather than the
main application workload.

4. **PORT AND PROTOCOL ANALYSIS**:
   - Ports are primarily RabbitMQ node-related:
     - **4369** (epmd—Erlang Port Mapper Daemon for clustering)
     - **25672** (RabbitMQ cluster communication).
   - These confirm it as a supporting RabbitMQ component for clustering, not the core service.

**Decision**: Low confidence (supporting infrastructure rather than core service).
❌ **Do not add workload**.

---

### **Analysis of "investibots-service"**
1. **SERVICE NAME ANALYSIS**:
   - Name appears custom or proprietary ("investibots"). No indication of a widely used OSS project.

2. **NAMESPACE ANALYSIS**:
   - Default namespace is neutral.

3. **LABELS AND ANNOTATIONS ANALYSIS**:
   - No OSS-related labels.

4. **PORT AND PROTOCOL ANALYSIS**:
   - **80** (HTTP) is generic and provides no specific indication.

**Decision**: Low confidence (custom, non-OSS workload).
❌ **Do not add workload**.

---

### **Analysis of "kubernetes"**
1. **SERVICE NAME ANALYSIS**:
   - This is the default Kubernetes API service, a system component.

**Decision**: Excluded by rule (system component).
❌ **Do not add workload**.

---

### **Analysis of "nginx-project"**
1. **SERVICE NAME ANALYSIS**:
   - "nginx" indicates the core workload of NGINX, a widely used OSS web server/proxy.

2. **NAMESPACE ANALYSIS**:
   - Default namespace is neutral.

3. **LABELS AND ANNOTATIONS ANALYSIS**:
   - Generic labels but annotations show a link to NGINX (`"app":"nginx-project"`).

4. **PORT AND PROTOCOL ANALYSIS**:
   - Port **80** (HTTP) is consistent with NGINX workloads.

**Decision**: High confidence that this is an NGINX core workload.
✅ **Add workload**: "nginx-project"

---

### **Analysis of "prometheus-reference-service"**
1. **SERVICE NAME ANALYSIS**:
   - Name mentions Prometheus, but it does not directly align with the core Prometheus server.

2. **NAMESPACE ANALYSIS**:
   - Default namespace is neutral.

3. **LABELS AND ANNOTATIONS ANALYSIS**:
   - Labels (`'app': 'prometheus-reference-app'`) and annotations suggest it is an exporter and custom
metrics collector rather than the core Prometheus service.

4. **PORT AND PROTOCOL ANALYSIS**:
   - Ports are unrelated to the Prometheus core server (custom metrics endpoints: 2112, 2113, and
2114).

**Decision**: Low confidence (monitoring exporter).
❌ **Do not add workload**.

---

### **Analysis of "rabbitmq-rabbitmq-messaging-topology-operator-webhook"**
1. **SERVICE NAME ANALYSIS**:
   - Name indicates it is a supporting operator service (webhook) for RabbitMQ rather than the core
workload.

**Decision**: Excluded by rule (operator or webhook service).
❌ **Do not add workload**.

---

### **Analysis of "my-cluster-kafka-bootstrap"**
1. **SERVICE NAME ANALYSIS**:
   - Name indicates it is a bootstrap service for Kafka, not the core Kafka brokers.

**Decision**: Excluded by rule (bootstrap service).
❌ **Do not add workload**.

---

### **Analysis of "my-cluster-kafka-brokers"**
1. **SERVICE NAME ANALYSIS**:
   - Name strongly suggests it is part of Kafka's core brokers, indicating a major OSS project.

2. **NAMESPACE ANALYSIS**:
   - Namespace "kafka" matches the workload name.

3. **LABELS AND ANNOTATIONS ANALYSIS**:
   - Labels confirm it is part of Kafka (`'strimzi.io/component-type': 'kafka'`,
`'strimzi.io/cluster': 'my-cluster'`, `'strimzi.io/kind': 'Kafka'`).

4. **PORT AND PROTOCOL ANALYSIS**:
   - Prominent Kafka ports are present:
     - **9092** (client connections)
     - **9093** (TLS connections).

**Decision**: High confidence that this is a core Kafka brokers service.
✅ **Add workload**: "my-cluster-kafka-brokers"

---

### **Outcome**

Detected high-confidence OSS workloads:
- "hello-world"
- "nginx-project"
- "my-cluster-kafka-brokers"
                       """))