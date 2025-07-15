import k8s.client
from . import tools
from . import models
from . import prompts
from utils import printer
from pydantic import BaseModel
from langgraph.types import interrupt
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.callbacks import get_openai_callback

class Workflow(BaseModel):
    thread_id: str = None

    detected_workloads: dict[str, k8s.client.Workload] = None
    detected_oss_workloads: dict[str, k8s.client.Workload] = None
    selected_oss_workloads: dict[str, k8s.client.Workload] = None

def detect_workloads(workflow: Workflow) -> dict[str, k8s.client.Workload]:
    """Detect workloads in the Kubernetes cluster."""


    k8s_client = k8s.client.K8sClient("/mnt/c/Users/t-arohatgi/.kube/config")
    detected_workloads = k8s.client.detect_workloads(k8s_client)

    printer.banner("Detected Workloads")
    printer.out(
        "\n".join(f"🔨 Workload: {workload.name} in namespace {workload.namespace}" for workload in detected_workloads)    )
    printer.banner("Detected Workloads")

    detected_workloads_dict = {workload.name.lower(): workload for workload in detected_workloads}

    return {
        "detected_workloads": detected_workloads_dict
    }


def detect_oss_workloads(workflow: Workflow) -> dict[str, k8s.client.Workload]:
    detected_oss_workload_names = []  # Reset the global list
    
    # temporary function to add OSS workload names
    def add_oss_workload(workload_name: str) -> str:
        """Add a workload name to the detected OSS workloads list.
        
        Args:
            workload_name: The name of the workload to add to the OSS workloads list
            
        Returns:
            Confirmation message
        """

        detected_oss_workload_names.append(workload_name.lower())
        return f"Added {workload_name} to the detected OSS workloads list"

    oss_detection_agent = create_react_agent(
        models.llm_4o_mini,
        tools=[add_oss_workload],
        prompt=prompts.OSS_DETECTION_PROMPT)

    # Prepare workload information for the agent
    workload_info = tools.generate_workload_info(workflow.detected_workloads)

    # Create the analysis prompt for the agent
    analysis_prompt = tools.generate_workload_detection_analysis_prompt(workload_info)

    # Run the agent
    try:
        with get_openai_callback() as callback:
            _ = oss_detection_agent.invoke({"messages": [{"role": "user", "content": analysis_prompt}]})
            # printer.out(response)


        printer.banner("AI Agent Tokens and Cost")
        printer.out(f"💵 Total tokens used: {callback.total_tokens}\n" + f"💵 Prompt tokens: {callback.prompt_tokens}\n" + f"💵 Completion tokens: {callback.completion_tokens}\n" + f"💵 Total cost: ${callback.total_cost:.6f}")
        printer.banner("AI Agent Tokens and Cost")

    except Exception as e:
        printer.error(f"AI Agent analysis failed: {str(e)}")

    # Build the detected OSS workloads dictionary
    detected_oss_workloads = {}
    for workload_name in detected_oss_workload_names:
        if workload_name in workflow.detected_workloads:
            detected_oss_workloads[workload_name] = workflow.detected_workloads[workload_name]

    printer.banner("Detected OSS Workloads")
    printer.out(
        "\n".join(f"🔍 {name}: {workload.image}" for name, workload in detected_oss_workloads.items())  )
    printer.banner("Detected OSS Workloads")

    return {
        "detected_oss_workloads": detected_oss_workloads
    }

def select_oss_workloads(workflow: Workflow) -> dict[str, k8s.client.Workload]:
    selected_workloads = interrupt({
        "detected_oss_workloads": list(workflow.detected_oss_workloads.keys()),
    })

    printer.banner("Selected OSS Workloads")
    printer.out(
        "\n".join(f"✅ {name}" for name in selected_workloads)
    )
    printer.banner("Selected OSS Workloads")

    if selected_workloads:
        selected_oss_workloads = {
            name: workload for name, workload in workflow.detected_oss_workloads.items()
            if name in selected_workloads
        }

    return {
        "selected_oss_workloads": selected_oss_workloads
    }

def build_graph() -> StateGraph:
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
    return graph

graph = build_graph()