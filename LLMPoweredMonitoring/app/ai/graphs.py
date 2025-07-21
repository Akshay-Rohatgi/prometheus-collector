from k8s import client as k8s_client
from . import tools, models, prompts
from .utils import print_utils, agent_utils, workload_utils, gh_utils
from .config import K8S_CONFIG_PATH, MAX_EVALUATION_ROUNDS, OSS_WORKLOAD_EMOJI
from printer import printer
from typing import Dict, Optional
from pydantic import BaseModel
from langgraph.types import interrupt
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.checkpoint.memory import MemorySaver


class MonitoringPlan(BaseModel):
    markdown_plan: str = None

class MonitoringFeedback(BaseModel):
    round_count: int = 0
    critic_approved: bool = False
    feedback_text: str = None

class Workflow(BaseModel):
    thread_id: str = None

    detected_workloads: dict[str, k8s_client.Workload] = None
    detected_oss_workloads: dict[str, k8s_client.Workload] = None
    selected_oss_workloads: dict[str, k8s_client.Workload] = None

    verified_oss_workloads: dict[str, k8s_client.Workload] = None
    confirmed_to_plan: bool = None

    monitoring_plan_approval: bool = None
    monitoring_plan_feedback: MonitoringFeedback = None
    monitoring_plans: dict[str, MonitoringPlan] = None

def detect_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Detect workloads in the Kubernetes cluster."""
    client = k8s_client.K8sClient(K8S_CONFIG_PATH)
    detected_workloads = k8s_client.detect_workloads(client)
    
    detected_workloads_dict = {
        workload.name.lower(): workload for workload in detected_workloads
    }
    print_utils.print_workload_list("Detected Workloads", detected_workloads_dict)
    
    return {"detected_workloads": detected_workloads_dict}


def detect_oss_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Detect OSS workloads using an AI agent based on the detected workloads."""
    detected_oss_workload_names = []

    def add_oss_workload(workload_name: str) -> str:
        """Add a workload name to the detected OSS workloads list."""
        detected_oss_workload_names.append(workload_name.lower())
        return f"Added {workload_name} to the detected OSS workloads list"

    analysis_prompt = tools.generate_workload_detection_analysis_prompt(
        workflow.detected_workloads
    )
    
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        tools=[add_oss_workload],
        agent_prompt=prompts.NEW_OSS_DETECTION_PROMPT
    )
    
    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        if response_content:
            printer.out(response_content)

        detected_oss_workloads = workload_utils.filter_workloads(
            workflow.detected_workloads, 
            detected_oss_workload_names
        )
        print_utils.print_workload_list(
            "Detected OSS Workloads", 
            detected_oss_workloads, 
            OSS_WORKLOAD_EMOJI
        )
        return {"detected_oss_workloads": detected_oss_workloads}
    
    return {"detected_oss_workloads": {}}


def select_oss_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """User selects which OSS workloads to monitor from the detected OSS workloads."""
    selected_workloads = interrupt(
        {"detected_oss_workloads": list(workflow.detected_oss_workloads.keys())}
    )

    if not selected_workloads:
        return {"selected_oss_workloads": {}}

    selected_oss_workloads = workload_utils.filter_workloads(
        workflow.detected_oss_workloads, 
        selected_workloads
    )
    print_utils.print_workload_list(
        "Selected OSS Workloads",
        selected_oss_workloads,
        "✅"
    )

    return {"selected_oss_workloads": selected_oss_workloads}


def verify_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Verify that the selected OSS workloads are not already being monitored."""
    client = k8s_client.K8sClient(K8S_CONFIG_PATH)

    # This is a placeholder for the actual verification logic
    # k8s_client.verify_workloads(client, workflow.selected_oss_workloads)
    verified_workloads = workflow.selected_oss_workloads.copy()

    return {"verified_oss_workloads": verified_workloads}


def confirmation_before_planning(workflow: Workflow) -> dict[str, bool]:
    """Request confirmation to proceed with monitoring deployment plan generation."""
    begin_approval = interrupt({"message": "Do you want to generate a monitoring deployment plan for the selected OSS workloads?"})

    status = "Confirmed" if begin_approval else "Not confirmed"
    printer.info(f"{status} to generate monitoring deployment plan.")

    return {"confirmed_to_plan": begin_approval}


def generate_monitoring_deployment_plan(workflow: Workflow) -> dict[str, MonitoringPlan]:
    """Generate a monitoring deployment plan using an AI agent."""
    monitoring_plans = {}
    
    # Check if we have verified workloads
    if not workflow.verified_oss_workloads or len(workflow.verified_oss_workloads) == 0:
        printer.error("No verified OSS workloads found to generate monitoring plans for.")
        return {"monitoring_plans": {}}
    
    workload_name, workload = workload_utils.get_first_workload(workflow.verified_oss_workloads)

    # Tool for getting chart.yaml version number
    def get_chart_yaml_version(exporter_name: str) -> str:
        """Get the latest version from Chart.yaml for a prometheus exporter."""
        try:
            # Get GitHub client and repo
            github_client = gh_utils.get_github_client()
            repo = gh_utils.get_repo(github_client, "prometheus-community/helm-charts")
            
            # Get Chart.yaml content from the exporter directory
            chart_dir = f"charts/prometheus-{exporter_name}-exporter"
            try:
                directory_content = gh_utils.get_directory_content(repo, chart_dir)
                chart_content = gh_utils.get_file_content_from_directory(repo, directory_content, "Chart.yaml")
                
                # Parse the YAML to extract version
                import yaml
                chart_data = yaml.safe_load(chart_content)
                version = chart_data.get('version', 'Version not found')
                
                return f"Latest version for prometheus-{exporter_name}-exporter: {version}"
            except Exception as e:
                return f"Could not find chart for prometheus-{exporter_name}-exporter: {str(e)}"
        except Exception as e:
            return f"Error accessing GitHub repository: {str(e)}"

    # Determine if this is an improvement iteration
    is_improvement = (workflow.monitoring_plan_feedback is not None and workflow.monitoring_plan_feedback.round_count > 0)

    message = "Improving" if is_improvement else "Generating"
    printer.info(
        f"{message} monitoring deployment plan for {workload.name}"
        + (f" (Round {workflow.monitoring_plan_feedback.round_count})" if is_improvement else "")
    )

    # Prepare the analysis prompt based on whether this is an improvement iteration
    if is_improvement:
        previous_plan = workflow.monitoring_plans.get(workload_name)
        previous_feedback = workflow.monitoring_plan_feedback.feedback_text
        
        analysis_prompt = f"""
        You need to IMPROVE the existing monitoring deployment plan based on the critic's feedback.

        {workload_utils.format_workload_info(workload)}
        
        PREVIOUS PLAN:
        ## Human Readable Summary
        {previous_plan.markdown_plan or 'No summary provided'}

        CRITIC FEEDBACK:
        {previous_feedback}
        
        Please ADDRESS the critic's feedback and generate an IMPROVED monitoring deployment plan.
        Use the update_monitoring_plan function to provide your improved plan.
        """
    else:
        analysis_prompt = tools.generate_monitoring_plan_prompt(workload)

    # Run the optimizer agent
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        tools=[get_chart_yaml_version],
        agent_prompt=prompts.NEW_MONITORING_PLAN_GENERATION_PROMPT
    )
    
    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        if response_content:
            monitoring_plans[workload_name] = MonitoringPlan(markdown_plan=response_content)
            printer.success(f"Generated monitoring plan for {workload_name}")
        else:
            printer.warning("Agent response was empty, generating fallback plan")
            monitoring_plans[workload_name] = MonitoringPlan(
                markdown_plan="# Fallback Monitoring Plan\n\nAgent failed to generate response content. Please try regenerating the plan."
            )
    else:
        printer.error("Agent failed to respond, generating fallback plan")
        monitoring_plans[workload_name] = MonitoringPlan(
            markdown_plan="# Fallback Monitoring Plan\n\nAgent failed to generate a response. Please check the agent configuration and try again."
        )

    return {"monitoring_plans": monitoring_plans}

def evaluate_monitoring_deployment_plan(workflow: Workflow) -> dict[str, MonitoringFeedback]:
    """Evaluate the monitoring deployment plan using a critic agent."""
    # Initialize or get existing feedback
    feedback = workflow.monitoring_plan_feedback or MonitoringFeedback(round_count=0, critic_approved=False)
    feedback.round_count += 1
    
    # Check if we've hit the max rounds
    if feedback.round_count > MAX_EVALUATION_ROUNDS - 1:
        printer.warning(f"Maximum evaluation rounds ({MAX_EVALUATION_ROUNDS}) reached. Automatically approving plan.")
        feedback.critic_approved = True
        feedback.feedback_text = "Maximum evaluation rounds reached. Plan approved by default."
        return {"monitoring_plan_feedback": feedback}
    
    printer.info(f"Evaluating monitoring deployment plan (Round {feedback.round_count}/{MAX_EVALUATION_ROUNDS})...")
    
    # Check if monitoring plans exist
    if not workflow.monitoring_plans or len(workflow.monitoring_plans) == 0:
        printer.error("No monitoring plans found to evaluate. Setting feedback as failed.")
        feedback.critic_approved = False
        feedback.feedback_text = "No monitoring plans were generated. Please regenerate the monitoring plan."
        return {"monitoring_plan_feedback": feedback}
    
    # Get the first monitoring plan
    workload_name, monitoring_plan = workload_utils.get_first_workload(workflow.monitoring_plans)
    
    # Prepare the evaluation prompt
    plan_text = f"""
    Monitoring Plan for {workload_name}:
    
    ## Markdown Formatted Plan
    {monitoring_plan.markdown_plan or 'No plan provided'}
    """

    # Include previous feedback if this is not the first round
    previous_feedback = ""
    if feedback.round_count > 1 and feedback.feedback_text:
        previous_feedback = f"\n\n## Previous Feedback (Round {feedback.round_count - 1})\n{feedback.feedback_text}"

    evaluation_prompt = f"""
    Please evaluate the following monitoring deployment plan:
    
    {plan_text}
    {previous_feedback}
    
    This is evaluation round {feedback.round_count} of {MAX_EVALUATION_ROUNDS}. 
    Provide comprehensive feedback and determine if the plan should be approved or needs improvement.
    Use the provide_feedback function to give your evaluation.
    """

    # Run the critic agent
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=evaluation_prompt,
        agent_prompt=prompts.MONITORING_PLAN_EVALUATOR_PROMPT
    )
    
    if response:
        feedback.feedback_text = agent_utils.AgentManager.get_agent_response_content(response)
        
        if feedback.feedback_text:
            printer.banner("Critic Feedback")
            printer.out(feedback.feedback_text)
            printer.banner("Critic Feedback")

            # The critic's response should indicate approval/disapproval
            feedback.critic_approved = "approved" in feedback.feedback_text.lower()
            status_message = "✅ Monitoring plan approved by critic!" if feedback.critic_approved else "❌ Monitoring plan needs improvement."
            printer.success(status_message) if feedback.critic_approved else printer.warning(status_message)
    else:
        feedback.critic_approved = False
        feedback.feedback_text = "Critic agent failed to generate feedback"
        printer.error(feedback.feedback_text)

    return {"monitoring_plan_feedback": feedback}


def approve_monitoring_deployment_plan(workflow: Workflow) -> dict[str, bool]:
    """Request final approval for the generated monitoring deployment plan."""
    approval = interrupt({"monitoring_plans": workflow.monitoring_plans})

    status = "approved" if approval else "not approved"
    if approval: printer.success(f"Monitoring deployment plan {status}.")
    else: printer.warning(f"Monitoring deployment plan {status}.")

    return {"monitoring_plan_approval": approval}


def route_before_planning(workflow: Workflow) -> bool:
    """Determine whether to proceed with plan generation or end workflow."""
    return bool(workflow.confirmed_to_plan)

def route_after_evaluation(workflow: Workflow) -> str:
    """Determine next step based on critic feedback and evaluation rounds."""
    feedback = workflow.monitoring_plan_feedback
    
    if (
        feedback.critic_approved 
        or feedback.round_count >= MAX_EVALUATION_ROUNDS - 1
    ):
        return "approve_monitoring_deployment_plan"
    
    return "generate_monitoring_deployment_plan"

def build_graph() -> StateGraph:
    builder = StateGraph(Workflow)

    # NODES
    builder.add_node("detect_workloads", detect_workloads)
    builder.add_node("detect_oss_workloads", detect_oss_workloads)
    builder.add_node("select_oss_workloads", select_oss_workloads)
    builder.add_node("verify_workloads", verify_workloads)
    builder.add_node("confirmation_before_planning", confirmation_before_planning)
    builder.add_node("generate_monitoring_deployment_plan", generate_monitoring_deployment_plan)
    builder.add_node("evaluate_monitoring_deployment_plan", evaluate_monitoring_deployment_plan)
    builder.add_node("approve_monitoring_deployment_plan", approve_monitoring_deployment_plan)

    # EDGES
    # Pod Scanning and Workflow Identification Phase
    # START -> detect_workloads -> detect_oss_workloads -> select_oss_workloads -> verify_workloads
    builder.add_edge(START, "detect_workloads")
    builder.add_edge("detect_workloads", "detect_oss_workloads")
    builder.add_edge("detect_oss_workloads", "select_oss_workloads")
    builder.add_edge("select_oss_workloads", "verify_workloads")

    # Intermediary phase between workload detection and planning - opportunity to exit workflow
    builder.add_edge("verify_workloads", "confirmation_before_planning")
    builder.add_conditional_edges(
        "confirmation_before_planning",
        route_before_planning,
        {True: "generate_monitoring_deployment_plan", False: END},
    )

    # Optimizer-Evaluator Loop
    builder.add_edge("generate_monitoring_deployment_plan", "evaluate_monitoring_deployment_plan")
    builder.add_conditional_edges(
        "evaluate_monitoring_deployment_plan",
        route_after_evaluation,
        {
            "generate_monitoring_deployment_plan": "generate_monitoring_deployment_plan",
            "approve_monitoring_deployment_plan": "approve_monitoring_deployment_plan"
        },
    )

    builder.add_edge("approve_monitoring_deployment_plan", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


graph = build_graph()
