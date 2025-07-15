import time
from typing import List
import classes
import k8s
from pydantic import BaseModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from langchain_community.callbacks import get_openai_callback

# Global variable to store detected OSS workload names
# detected_oss_workload_names = []

class Workflow(BaseModel):
    thread_id: str = None

    detected_workloads: dict[str, k8s.Workload] = None
    detected_oss_workloads: dict[str, k8s.Workload] = None
    selected_oss_workloads: dict[str, k8s.Workload] = None

load_dotenv()
llm = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",
    api_version="2024-12-01-preview",
)

# Tool for the OSS workload detection agent


def detect_workloads(workflow: Workflow) -> dict[str, k8s.Workload]:
    print("Detecting workloads...")

    k8s_client = k8s.K8sClient("/mnt/c/Users/t-arohatgi/.kube/config")
    detected_workloads = k8s.detect_workloads(k8s_client)

    print(
        "=== Detected Workloads ===\n" +
        "\n".join(f"🔨 Workload: {workload.name} in namespace {workload.namespace}" for workload in detected_workloads) +
        "\n" +
        "=== Detected Workloads ==="
    )

    detected_workloads_dict = {workload.name.lower(): workload for workload in detected_workloads}

    return {
        "detected_workloads": detected_workloads_dict
    }

def detect_oss_workloads(workflow: Workflow) -> dict[str, k8s.Workload]:
    detected_oss_workload_names = []  # Reset the global list
    
    def add_oss_workload(workload_name: str) -> str:
        """Add a workload name to the detected OSS workloads list.
        
        Args:
            workload_name: The name of the workload to add to the OSS workloads list
            
        Returns:
            Confirmation message
        """
        # global detected_oss_workload_names
        detected_oss_workload_names.append(workload_name.lower())
        return f"Added {workload_name} to the detected OSS workloads list"

    oss_detection_agent = create_react_agent(
        llm,
        tools=[add_oss_workload],
        prompt="""You are an expert Kubernetes and open-source software analyst. Your task is to identify major, first-class OSS workloads that would benefit from Prometheus monitoring.

    OBJECTIVE:
    Analyze the provided Kubernetes workloads and identify which ones are significant open-source software projects that:
    1. Are widely used in production environments
    2. Have established monitoring patterns
    3. Would benefit from Prometheus exporters
    4. Are NOT system/infrastructure components managed by cloud providers

    ANALYSIS METHODOLOGY:
    Follow these steps systematically for each workload:

    1. **IMAGE ANALYSIS** (Primary Signal):
    - Examine the container image registry and name
    - Look for official images from:
        * Docker Hub official images (library/)
        * Quay.io official repositories
        * GitHub Container Registry (ghcr.io)
        * Project-specific registries
    - Examples of OSS image patterns:
        * kafka, zookeeper, elasticsearch, redis, mongodb
        * nginx, apache, traefik, istio, envoy
        * prometheus, grafana, jaeger, zipkin
        * postgresql, mysql, cassandra, influxdb
        * rabbitmq, nats, activemq

    2. **METADATA LABELS ANALYSIS** (Secondary Signal):
    - Check for Helm chart labels (helm.sh/chart, app.kubernetes.io/name)
    - Look for application labels (app.kubernetes.io/instance, app.kubernetes.io/component)
    - Identify operator-managed workloads (app.kubernetes.io/managed-by)
    - Check for service mesh annotations (istio.io/, linkerd.io/)

    3. **ENVIRONMENT VARIABLES ANALYSIS** (Tertiary Signal):
    - Look for configuration that indicates OSS software
    - Database connection strings, message broker configs
    - Service discovery configurations
    - Authentication/authorization settings

    4. **REFERENCE CHECK**:
    Use the Prometheus community Helm charts as a reference for what has established monitoring patterns:
    https://github.com/prometheus-community/helm-charts/tree/main/charts
    
    Known categories include:
    - Databases: postgres, mysql, redis, elasticsearch, mongodb, cassandra
    - Message Brokers: kafka, rabbitmq, nats, activemq
    - Web Servers: nginx, apache, traefik
    - Service Mesh: istio, linkerd, consul
    - Monitoring: prometheus, grafana, jaeger, alertmanager
    - Storage: minio, ceph, rook
    - CI/CD: jenkins, argo, tekton
    - API Gateways: kong, ambassador, contour

    CONFIDENCE LEVELS:
    - HIGH: Official images, well-known OSS projects, established monitoring patterns
    - MEDIUM: Recognizable OSS projects but less common or newer
    - LOW: Unclear origin, custom applications, or minimal monitoring value

    EXCLUSION CRITERIA:
    - Cloud provider managed services (Azure, AWS, GCP prefixed)
    - Kubernetes system components (kube-*, coredns, etc.)
    - Custom/proprietary applications without clear OSS lineage
    - Development/testing tools not suitable for production monitoring
    - Operators that are just managing other services (unless the operator itself is significant)

    DECISION PROCESS:
    For each workload, provide your analysis and confidence level. Only invoke the add_oss_workload tool for workloads you have HIGH confidence are major, first-class OSS projects.

    When you find a workload that meets the criteria, call add_oss_workload(workload_name) to add it to the detected list.

    Remember: Quality over quantity. It's better to miss a few edge cases than to include workloads that don't truly benefit from monitoring or aren't significant OSS projects."""
    )

    # print("Detecting OSS workloads using AI agent...")
    
    # Prepare workload information for the agent
    workload_info = []
    for workload in workflow.detected_workloads.values():
        workload_details = {
            "name": workload.name,
            "image": workload.image,
            "namespace": workload.namespace,
            "labels": workload.metadata_labels,
            "containers": workload.containers
        }
        workload_info.append(workload_details)
    
    # Create the analysis prompt for the agent
    analysis_prompt = f"""Please analyze the following Kubernetes workloads and identify which ones are major, first-class OSS workloads suitable for Prometheus monitoring.

WORKLOADS TO ANALYZE:
"""
    
    for w in workload_info:
        analysis_prompt += f"""
Workload: {w['name']}
Image: {w['image']}
Namespace: {w['namespace']}
Labels: {w['labels']}
Containers: {w['containers']}
---
"""
    
    analysis_prompt += """
For each workload you identify as a major OSS project, use the add_oss_workload tool to add it to the detected list.
"""
    
    # Run the agent
    try:
        with get_openai_callback() as callback:
            response = oss_detection_agent.invoke({"messages": [{"role": "user", "content": analysis_prompt}]})

        print("=== AI Agent Tokens and Cost ===")
        print(f"💵 Total tokens used: {callback.total_tokens}\n" + f"💵 Prompt tokens: {callback.prompt_tokens}\n" + f"💵 Completion tokens: {callback.completion_tokens}\n" + f"💵 Total cost: ${callback.total_cost:.6f}")
        print("=== AI Agent Tokens and Cost ===")

    except Exception as e:
        print(str(e))
        print(f"AI Agent analysis failed: {e}")
        # Fallback to simple detection
        detected_oss_workload_names = []
        simple_oss_patterns = ["kafka", "elasticsearch", "redis", "mongodb", "postgresql", "mysql", "nginx", "prometheus", "grafana", "rabbitmq", "zookeeper", "cassandra", "influxdb", "jenkins", "argo", "istio", "traefik", "consul", "vault", "minio", "jaeger", "zipkin"]
        for workload in workflow.detected_workloads.values():
            if any(pattern in workload.name.lower() or pattern in workload.image.lower() for pattern in simple_oss_patterns):
                detected_oss_workload_names.append(workload.name.lower())
    
    # Build the detected OSS workloads dictionary
    detected_oss_workloads = {}
    for workload_name in detected_oss_workload_names:
        if workload_name in workflow.detected_workloads:
            detected_oss_workloads[workload_name] = workflow.detected_workloads[workload_name]
    
    print(
        "=== Detected OSS Workloads ===\n" +
        "\n".join(f"🔍 {name}: {workload.image}" for name, workload in detected_oss_workloads.items()) +
        "\n" +
        "=== Detected OSS Workloads ==="
    )

    return {
        "detected_oss_workloads": detected_oss_workloads
    }


def select_oss_workloads(workflow: Workflow) -> dict[str, k8s.Workload]:
    selected_workloads = interrupt({
        "detected_oss_workloads": list(workflow.detected_oss_workloads.keys()),
    })

    print(
        "=== Selected OSS Workloads ===\n" +
        "\n".join(f"✅ {name}" for name in selected_workloads) +
        "\n" +
        "=== Selected OSS Workloads ==="
    )

    if selected_workloads:
        selected_oss_workloads = {
            name: workload for name, workload in workflow.detected_oss_workloads.items()
            if name in selected_workloads
        }

    return {
        "selected_oss_workloads": selected_oss_workloads
    }

builder = StateGraph(Workflow)
builder.add_node("detect_workloads", detect_workloads)
builder.add_node("detect_oss_workloads", detect_oss_workloads)
builder.add_node("select_oss_workloads", select_oss_workloads)

builder.add_edge(START, "detect_workloads")
builder.add_edge("detect_workloads", "detect_oss_workloads")
builder.add_edge("detect_oss_workloads", "select_oss_workloads")
builder.add_edge("select_oss_workloads", END)


checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)