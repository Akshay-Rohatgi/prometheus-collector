import time
import classes
from pydantic import BaseModel
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver

class Workflow(BaseModel):
    thread_id: str = None

    detected_workloads: dict[str, classes.Workload] = None
    detected_oss_workloads: dict[str, classes.Workload] = None
    selected_oss_workloads: dict[str, classes.Workload] = None

def detect_workloads(workflow: Workflow) -> dict[str, classes.Workload]:
    kafka_workload = classes.Workload(name="Kafka")
    elasticsearch_workload = classes.Workload(name="Elasticsearch")
    custom_workload = classes.Workload(name="Hello-World")

    detected_workloads = {
        "kafka": kafka_workload,
        "elasticsearch": elasticsearch_workload,
        "custom": custom_workload
    }

    print(
        "=== Detected Workloads ===\n" +
        "\n".join(f"- {name}: {workload}" for name, workload in detected_workloads.items()) +
        "\n" +
        "=== Detected Workloads ==="
    )

    return {
        "detected_workloads": detected_workloads
    }

def detect_oss_workloads(workflow: Workflow) -> dict[str, classes.Workload]:
    oss_workloads = {"kafka", "elasticsearch", "argo", "istio", "nginx"}
    detected_oss_workloads = {}
    
    print("Detecting OSS workloads...")
    time.sleep(1)

    for workload in workflow.detected_workloads.values():
        if workload.name.lower() in oss_workloads:
            detected_oss_workloads[workload.name.lower()] = workload

    print(
        "=== Detected OSS Workloads ===\n" +
        "\n".join(f"- {name}: {workload}" for name, workload in detected_oss_workloads.items()) +
        "\n" +
        "=== Detected OSS Workloads ==="
    )

    return {
        "detected_oss_workloads": detected_oss_workloads
    }


def select_oss_workloads(workflow: Workflow) -> dict[str, classes.Workload]:
    selected_workloads = interrupt({
        "detected_oss_workloads": list(workflow.detected_oss_workloads.keys()),
    })

    print(
        "=== Selected OSS Workloads ===\n" +
        "\n".join(f"- {name}" for name in selected_workloads) +
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