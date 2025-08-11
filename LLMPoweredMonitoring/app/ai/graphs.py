from k8s import client as k8s_client
from . import tools, models, prompts
from .utils import print_utils, agent_utils, workload_utils
from .config import K8S_CONFIG_PATH, MAX_EVALUATION_ROUNDS, OSS_WORKLOAD_EMOJI
from .instructions import MonitoringInstruction
from .deployment.controller import InstructionController
from printer import printer
from pydantic import BaseModel
from langgraph.types import interrupt
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.checkpoint.memory import MemorySaver
from logs import get_logger, log_with_context
import time

# Initialize logger
logger = get_logger(__name__)

class MonitoringPlan(BaseModel):
    markdown_plan: str = None
    structured_plan: list[MonitoringInstruction] = None

class MonitoringFeedback(BaseModel):
    round_count: int = 0
    critic_approved: bool = False
    feedback_text: str = None

class Workflow(BaseModel):
    thread_id: str = None

    detected_workloads: dict[str, k8s_client.Workload] = None
    detected_oss_workloads: dict[str, k8s_client.Workload] = None
    selected_oss_workload: k8s_client.Workload = None

    verified_oss_workload: k8s_client.Workload = None
    confirmed_to_plan: bool = None

    monitoring_plan_approval: bool = None
    monitoring_plan_feedback: MonitoringFeedback = None
    monitoring_plan: MonitoringPlan = None

    confirmed_to_plan: bool = None
    deployment_success: bool = None

    recommended_dashboards: dict[str, int] = None

def detect_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Detect workloads in the Kubernetes cluster."""
    start_time = time.time()
    
    logger.info("Starting workload detection", extra={
        'component': 'ai_graphs',
        'operation': 'detect_workloads',
        'workflow_phase': 'workload-detection'
    })
    
    try:
        client = k8s_client.K8sClient(K8S_CONFIG_PATH)
        detected_workloads = k8s_client.detect_workloads(client)
        
        detected_workloads_dict = {
            workload.name.lower(): workload for workload in detected_workloads
        }
        
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Workload detection completed", extra={
            'component': 'ai_graphs',
            'operation': 'detect_workloads',
            'workflow_phase': 'workload-detection',
            'duration_ms': duration_ms,
            'workloads_detected': len(detected_workloads_dict)
        })
        
        print_utils.print_workload_list("Detected Workloads", detected_workloads_dict)
        
        return {"detected_workloads": detected_workloads_dict}
        
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Workload detection failed: {e}", extra={
            'component': 'ai_graphs',
            'operation': 'detect_workloads',
            'workflow_phase': 'workload-detection',
            'duration_ms': duration_ms
        })
        raise


def detect_oss_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Detect OSS workloads using an AI agent based on the detected workloads."""
    start_time = time.time()
    
    logger.info("Starting OSS workload detection", extra={
        'component': 'ai_graphs',
        'operation': 'detect_oss_workloads',
        'workflow_phase': 'oss-detection',
        'input_workloads': len(workflow.detected_workloads or {})
    })
    
    try:
        detected_oss_workload_names = []
        add_oss_workload = tools.create_add_oss_workload_tool(detected_oss_workload_names)

        analysis_prompt = tools.generate_workload_detection_analysis_prompt(
            workflow.detected_workloads
        )
        
        response, _ = agent_utils.AgentManager.create_and_run_agent(
            prompt=analysis_prompt,
            tools=[add_oss_workload],
            model=models.llm_4o,
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
            
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info("OSS workload detection completed", extra={
                'component': 'ai_graphs',
                'operation': 'detect_oss_workloads',
                'workflow_phase': 'oss-detection',
                'duration_ms': duration_ms,
                'oss_workloads_detected': len(detected_oss_workloads)
            })
            
            print_utils.print_workload_list(
                "Detected OSS Workloads", 
                detected_oss_workloads, 
                OSS_WORKLOAD_EMOJI
            )
            return {"detected_oss_workloads": detected_oss_workloads}
        
        logger.warning("No OSS workloads detected by AI agent", extra={
            'component': 'ai_graphs',
            'operation': 'detect_oss_workloads',
            'workflow_phase': 'oss-detection'
        })
        return {"detected_oss_workloads": {}}
        
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"OSS workload detection failed: {e}", extra={
            'component': 'ai_graphs',
            'operation': 'detect_oss_workloads',
            'workflow_phase': 'oss-detection',
            'duration_ms': duration_ms
        })
        raise


def select_oss_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """User selects which OSS workload to monitor from the detected OSS workloads."""
    logger.info("User selection required for OSS workload", extra={
        'component': 'ai_graphs',
        'operation': 'select_oss_workloads',
        'workflow_phase': 'workload-selection',
        'available_workloads': len(workflow.detected_oss_workloads or {})
    })
    
    selected_workload_name = interrupt(
        {"detected_oss_workloads": list(workflow.detected_oss_workloads.keys())}
    )

    if not selected_workload_name:
        logger.warning("No workload selected by user", extra={
            'component': 'ai_graphs',
            'operation': 'select_oss_workloads',
            'workflow_phase': 'workload-selection'
        })
        return {"selected_oss_workload": None}

    # Since we're selecting only one workload, get the first one from the list
    if isinstance(selected_workload_name, list) and len(selected_workload_name) > 0:
        selected_workload_name = selected_workload_name[0]
    
    selected_oss_workload = workflow.detected_oss_workloads.get(selected_workload_name)
    
    if selected_oss_workload:
        printer.success(f"✅ Selected OSS Workload: {selected_oss_workload.name}")
    else:
        printer.warning("No valid workload selected")

    return {"selected_oss_workload": selected_oss_workload}


def verify_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Verify that the selected OSS workload is not already being monitored."""
    client = k8s_client.K8sClient(K8S_CONFIG_PATH)

    # This is a placeholder for the actual verification logic
    # k8s_client.verify_workloads(client, workflow.selected_oss_workload)
    verified_workload = workflow.selected_oss_workload

    return {"verified_oss_workload": verified_workload}


def confirmation_before_planning(workflow: Workflow) -> dict[str, bool]:
    """Request confirmation to proceed with monitoring deployment plan generation."""
    begin_approval = interrupt({"message": "Do you want to generate a monitoring deployment plan for the selected OSS workload?"})

    status = "Confirmed" if begin_approval else "Not confirmed"
    printer.info(f"{status} to generate monitoring deployment plan.")

    return {"confirmed_to_plan": begin_approval}


def generate_monitoring_deployment_plan(workflow: Workflow) -> dict[str, MonitoringPlan]:
    """Generate a monitoring deployment plan using an AI agent."""
    start_time = time.time()
    
    # Check if we have a verified workload
    if not workflow.verified_oss_workload:
        # Log missing workload error (system event)
        logger.error("Monitoring plan generation attempted without verified workload", extra={
            'component': 'ai_graphs',
            'operation': 'generate_monitoring_deployment_plan',
            'workflow_phase': 'monitoring-plan-generation',
            'error': 'no_verified_workload'
        })
        printer.error("No verified OSS workload found to generate monitoring plan for.")
        return {"monitoring_plan": None}
    
    workload = workflow.verified_oss_workload

    # Determine if this is an improvement iteration
    is_improvement = (workflow.monitoring_plan_feedback is not None and workflow.monitoring_plan_feedback.round_count > 0)
    round_number = workflow.monitoring_plan_feedback.round_count if workflow.monitoring_plan_feedback else 1

    # Log plan generation start (system event)
    logger.info("Monitoring plan generation started", extra={
        'component': 'ai_graphs',
        'operation': 'generate_monitoring_deployment_plan',
        'workflow_phase': 'monitoring-plan-generation',
        'workload_name': workload.name,
        'is_improvement': is_improvement,
        'round_number': round_number
    })

    message = "Improving" if is_improvement else "Generating"
    printer.info(
        f"{message} monitoring deployment plan for {workload.name}"
        + (f" (Round {round_number})" if is_improvement else "")
    )

    # Prepare the analysis prompt based on whether this is an improvement iteration
    if is_improvement:
        previous_plan = workflow.monitoring_plan
        if not previous_plan: previous_plan = MonitoringPlan(markdown_plan="No previous plan found.")
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

    # Run the generation agent
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        model=models.llm_4o,
        tools=[tools.get_chart_yaml_version, tools.get_values_yaml_formatted, tools.get_chart_readme, tools.search_values_keys],
        agent_prompt=prompts.NEW_MONITORING_PLAN_GENERATION_PROMPT
    )
    
    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        if response_content:
            monitoring_plan = MonitoringPlan(markdown_plan=response_content)
            printer.success(f"Generated monitoring plan for {workload.name}")
        else:
            printer.warning("Agent response was empty, generating fallback plan")
            monitoring_plan = MonitoringPlan(
                markdown_plan="# Fallback Monitoring Plan\n\nAgent failed to generate response content. Please try regenerating the plan."
            )
    else:
        printer.error("Agent failed to respond, generating fallback plan")
        monitoring_plan = MonitoringPlan(
            markdown_plan="# Fallback Monitoring Plan\n\nAgent failed to generate a response. Please check the agent configuration and try again."
        )

    return {"monitoring_plan": monitoring_plan}

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
    
    # Check if monitoring plan exists
    if not workflow.monitoring_plan:
        printer.error("No monitoring plan found to evaluate. Setting feedback as failed.")
        feedback.critic_approved = False
        feedback.feedback_text = "No monitoring plan was generated. Please regenerate the monitoring plan."
        return {"monitoring_plan_feedback": feedback}
    
    # Get the workload name for context
    workload_name = workflow.verified_oss_workload.name if workflow.verified_oss_workload else "Unknown"
    
    # Prepare the evaluation prompt
    plan_text = f"""
    Monitoring Plan for {workload_name}:
    
    ## Markdown Formatted Plan
    {workflow.monitoring_plan.markdown_plan or 'No plan provided'}
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
        model=models.llm_4o,
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
    approval = interrupt({"monitoring_plan": workflow.monitoring_plan})

    status = "approved" if approval else "not approved"
    if approval: printer.success(f"Monitoring deployment plan {status}.")
    else: printer.warning(f"Monitoring deployment plan {status}.")

    return {"monitoring_plan_approval": approval}

def structure_monitoring_deployment_plan(workflow: Workflow) -> dict[str, MonitoringPlan]:
    """Structure the monitoring deployment plan into a JSON format."""
    workload_name = workflow.verified_oss_workload.name if workflow.verified_oss_workload else "Unknown"
    printer.out(f"Structuring monitoring deployment plan of {workload_name} for agentic use...")

    instructions = []
    add_instruction = tools.create_add_instruction(instructions)
    structured_plan = tools.preprocess_markdown(workflow.monitoring_plan.markdown_plan)

    from rich.console import Console
    from rich.markdown import Markdown
    console = Console()
    console.print(Markdown(structured_plan))

    analysis_prompt = f"""
    You need to structure the monitoring deployment plan for {workload_name} into a JSON format
    {structured_plan or "No plan provided"}
    """

    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        model=models.llm_4o,
        tools=[add_instruction],
        agent_prompt=prompts.STRUCTURE_MONITORING_PLAN_PROMPT
    )

    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        if response_content:
            printer.success("Structured monitoring deployment plan successfully.")
            printer.out(response_content)
            try:
               workflow.monitoring_plan.structured_plan = instructions
               printer.out(f"Structured Plan: {workflow.monitoring_plan.structured_plan}")
            except Exception as e:
                printer.error(f"Failed to parse structured plan: {str(e)}")
                workflow.monitoring_plan = MonitoringPlan(markdown_plan="Error structuring plan.")
        else:
            printer.warning("Agent response was empty, structuring failed.")
            workflow.monitoring_plan = MonitoringPlan(markdown_plan="Error structuring plan.")


    return {"monitoring_plan": workflow.monitoring_plan}

def confirm_automated_monitoring_deployment(workflow: Workflow) -> dict[str, bool]:
    """Confirm whether to proceed with automated monitoring deployment."""
    confirmation = interrupt({
        "structured_plan": workflow.monitoring_plan.structured_plan,
        "message": "Do you want to proceed with automated deployment of this structured monitoring plan?"
    })
    return {"confirmed_to_plan": confirmation}

def deploy_structured_monitoring_plan(workflow: Workflow) -> dict[str, bool]:
    """Deploy the structured monitoring plan."""
    if not workflow.monitoring_plan or not workflow.monitoring_plan.structured_plan:
        printer.error("No structured monitoring plan found to deploy.")
        return {"deployment_success": False}
    
    controller = InstructionController()
    if controller.check_prerequisites():
        controller.set_instructions(workflow.monitoring_plan.structured_plan)
        printer.info(f"Deploying structured monitoring plan for {workflow.verified_oss_workload.name}...")
        success = controller.execute_plan(delete=False)
    else:
        workflow.deployment_success = False
        printer.error("Failed to meet prerequisites for deployment.")
        return {"deployment_success": False}

    if success:
        workflow.deployment_success = True
        printer.success("Structured monitoring plan deployed successfully.")
        return {"deployment_success": True}
    else:
        workflow.deployment_success = False
        printer.error("Failed to deploy structured monitoring plan.")
        return {"deployment_success": False}


def reccomend_dashboards(workflow: Workflow) -> dict[str, dict[str, int]]:
    """Recommend dashboards based on the structured monitoring plan."""
    if not workflow.monitoring_plan or not workflow.monitoring_plan.structured_plan:
        printer.error("No structured monitoring plan found to recommend dashboards.")
        return {"recommended_dashboards": {}}

    # Add interrupt to allow API query for dashboard recommendations
    get_recommendations = interrupt({
        "message": "Ready to generate dashboard recommendations. Call the API endpoint to proceed.",
        "workload_name": workflow.verified_oss_workload.name if workflow.verified_oss_workload else "Unknown",
        "monitoring_plan": workflow.monitoring_plan.markdown_plan
    })

    # If user chooses not to get recommendations, return empty dict
    if not get_recommendations:
        printer.info("Dashboard recommendations skipped.")
        return {"recommended_dashboards": {}}

    recommended_dashboards = {}
    add_recommended_dashboard = tools.create_add_recommended_dashboard_tool(recommended_dashboards)

    analysis_prompt = f"""You need to recommend Grafana dashboards based on the monitoring plan for {workflow.verified_oss_workload.name}.

    Here is the monitoring plan in markdown format:
    {workflow.monitoring_plan.markdown_plan}

    """
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        model=models.llm_5_mini,
        tools=[add_recommended_dashboard],
        agent_prompt=prompts.FIND_GRAFANA_DASHBOARD_PROMPT
    )
    
    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        if response_content:
            printer.success("Recommended dashboards successfully.")
            printer.out(response_content)
        else:
            printer.warning("Agent response was empty, no dashboards recommended.")
    print(f"Recommended Dashboards: {recommended_dashboards}")
    return {"recommended_dashboards": recommended_dashboards}

# routers
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

def route_after_confirmation(workflow: Workflow) -> bool:
    """Determine whether to proceed with automated monitoring deployment or end workflow."""
    return bool(workflow.confirmed_to_plan)

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
    builder.add_node("structure_monitoring_deployment_plan", structure_monitoring_deployment_plan)
    builder.add_node("confirm_automated_monitoring_deployment", confirm_automated_monitoring_deployment)
    builder.add_node("deploy_structured_monitoring_plan", deploy_structured_monitoring_plan)
    builder.add_node("reccomend_dashboards", reccomend_dashboards)

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

    # Deployment Planning Phase (Generator-Evaluator Loop)
    builder.add_edge("generate_monitoring_deployment_plan", "evaluate_monitoring_deployment_plan")
    builder.add_conditional_edges(
        "evaluate_monitoring_deployment_plan",
        route_after_evaluation,
        {
            "generate_monitoring_deployment_plan": "generate_monitoring_deployment_plan",
            "approve_monitoring_deployment_plan": "approve_monitoring_deployment_plan"
        },
    )

    builder.add_edge("approve_monitoring_deployment_plan", "structure_monitoring_deployment_plan")
    builder.add_edge("structure_monitoring_deployment_plan", "confirm_automated_monitoring_deployment")
    builder.add_conditional_edges(
        "confirm_automated_monitoring_deployment",
        route_after_confirmation,
        {True: "deploy_structured_monitoring_plan", False: "reccomend_dashboards"},
    )
    builder.add_edge("deploy_structured_monitoring_plan", "reccomend_dashboards")
    builder.add_edge("reccomend_dashboards", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


# Don't create a global graph - create a new one for each workflow
def get_graph():
    """Get a new graph instance for each workflow to avoid thread conflicts"""
    return build_graph()
