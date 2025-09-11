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
from logs import get_logger
import time
import os

# Initialize logger
logger = get_logger(__name__)

def build_enhanced_evaluator_prompt(workload: k8s_client.Workload, exporter_name: str = None) -> str:
    """Build an enhanced system prompt for the critic agent with workload context and values.yaml."""
    
    # Base evaluator prompt
    base_prompt = """You are an expert on deploying and evaluating managed Prometheus monitoring plans for Azure Managed Prometheus. Your task is to evaluate the provided monitoring deployment plan for a Kubernetes workload and provide feedback on its completeness, correctness, and adherence to best practices.

## Objective:
Evaluate the provided monitoring deployment plan for a Kubernetes workload and provide feedback on its completeness, correctness, and adherence to best practices. The plan should be comprehensive and include all necessary steps to deploy monitoring for Azure Managed Prometheus.

**Important** Everytime you make a critique do two things:
- provide EVIDENCE of why the critique is valid. If you cannot provide evidence then do not make the critique. Reference official Helm documentation or prometheus-community chart schemas. For example, if you are providing critique on a URI, reference official documentation or tool call output to make your claim. 
- Check to make sure that the critique does not violate any non-negotiables. The non-negotiables are:

### Non-Negotiables
- **CRITICAL**: The apiVersion for ServiceMonitors and PodMonitors must ALWAYS be "azmonitoring.coreos.com/v1" (NOT "monitoring.coreos.com/v1"). This is Azure-specific and required for Azure Managed Prometheus integration.
- **CRITICAL**: Helm release names must follow the deterministic pattern: azmon-{exporter}-exporter-{service}-{namespace}. Any deviation from this pattern MUST be rejected.
- Any NOT required configurations such as RBAC, SASL, TLS should be clearly marked as optional and not included in the main deployment plan. If you suggest these improvements remind the generator agent that it should be placed in an optional or extra steps section.

### Important Note About apiVersion:
- The values.yaml files you retrieve will show "monitoring.coreos.com/v1" as the default apiVersion - this is the standard Prometheus Operator format
- However, for Azure Managed Prometheus, you MUST override this to use "azmonitoring.coreos.com/v1" 
- This override is typically done via Helm parameters like: `--set serviceMonitor.apiVersion=azmonitoring.coreos.com/v1`
- Do NOT be confused by seeing "monitoring.coreos.com/v1" in the documentation - always enforce the Azure-specific version

## Enhanced Validation Criteria:
1. Service URI Format Validation:
   - Verify that any service URIs provided are in the correct format (servicename.namespace.svc.cluster.local or servicename.namespace)
   - Cross-reference against examples and instructions in the values.yaml documentation
   - Ensure the service names and namespaces align with the actual workload being monitored

2. Required Configuration Completeness:
   - Verify all necessary values are included in the deployment commands
   - **CRITICAL**: Ensure the apiVersion is explicitly set to "azmonitoring.coreos.com/v1" via Helm parameters
   - Check for **required** credentials, usernames, passwords, database names, connection strings, etc.
        - A common mistake the generation step makes is to forget database parameters for workloads such as MySQL
   - Ensure placeholder values exist for sensitive information (with proper warnings)
   - Validate that all required configuration parameters for the specific exporter are addressed
   - Any NOT required configurations such as RBAC, SASL, TLS should be clearly marked as optional and not included in the main deployment plan. If you suggest these improvements remind the generator agent that it should be placed in an optional or extra steps section.

3. Correctness and Best Practices:
   - Ensure that the plan correctly installs the necessary exporters and service monitors for the workload
   - Verify that the plan includes all necessary parameters and configurations for the workload
   - Ensure that optional sections are clearly marked as such
   - Validate security best practices (no sensitive info in plain text)

## Workload Context:"""
    
    # Add workload information
    workload_info = f"""
### Target Workload Information:
{workload_utils.format_workload_info(workload)}
"""
    
    # Add exporter context if provided
    exporter_context = ""
    if exporter_name:
        exporter_context = f"""
### Exporter Information:
- Expected Exporter: prometheus-{exporter_name}-exporter
- Base Service Name: {exporter_name} (use this for tool calls)

### Available Tools for Validation:
You have access to the following tools to get accurate helm chart information:
- **get_values_yaml(exporter_name)**: Gets the complete values.yaml content with comments preserved for a prometheus exporter. Pass the base service name (e.g., "kafka", "redis", "nginx") and it will look up the corresponding prometheus-{{name}}-exporter chart.
- **get_chart_readme(exporter_name)**: Gets the README.md content for a prometheus exporter chart, which contains usage examples, configuration notes, and best practices.
- **get_values_yaml_formatted(exporter_name)**: Gets the flattened key-value pairs from values.yaml for a prometheus exporter. Returns a dictionary with dot notation keys (e.g., "serviceMonitor.enabled": true) containing all configurable parameters.

**IMPORTANT**: When calling these tools, use only the base service name. For example:
- For a Kafka workload: call `get_values_yaml("kafka")` NOT `get_values_yaml("prometheus-kafka-exporter")`
- For a Redis workload: call `get_chart_readme("redis")` NOT `get_chart_readme("prometheus-redis-exporter")`
- For a Postgres workload: call `get_values_yaml_formatted("postgres")` NOT `get_values_yaml_formatted("prometheus-postgres-exporter")`

**CRITICAL REMINDER**: The values.yaml files will show "monitoring.coreos.com/v1" as the default, but you must ensure the monitoring plan overrides this to "azmonitoring.coreos.com/v1" for Azure compatibility.
"""
    
    # Combine all parts
    enhanced_prompt = base_prompt + workload_info + exporter_context + """

## Instructions:
- **ALWAYS** use the available tools to retrieve the official Helm chart documentation for validation
- Use the base service name (e.g., "{exporter_name}") when calling tools, not the full chart name
- Cross-reference the monitoring plan against the retrieved values.yaml documentation
- **CRITICAL**: Verify that the monitoring plan explicitly sets apiVersion to "azmonitoring.coreos.com/v1" via Helm parameters
- Pay special attention to service URI formats and required configuration parameters
- Validate that all necessary parameters are included with proper placeholder values for sensitive information
- Provide specific, actionable feedback for any issues found
- **REQUIRED**: You MUST use the approve_plan tool to make your final decision

## Final Decision Required:
After your evaluation, you MUST use the approve_plan tool to make your final decision. This tool requires:
- approved: boolean (True if plan is ready for deployment, False if it needs improvement)
- feedback: your detailed evaluation feedback explaining the decision
- critical_issues: list of critical issues if not approved (optional but recommended)

Example usage:
- If approved: approve_plan(True, "Plan meets all Azure Managed Prometheus requirements and follows best practices...")
- If rejected: approve_plan(False, "Plan has several critical issues that need attention...", ["Missing apiVersion override to azmonitoring.coreos.com/v1", "Incorrect service URI format"])

**IMPORTANT**: Your evaluation is not complete until you call approve_plan() with your final decision.""".format(exporter_name=exporter_name or "service")
    
    return enhanced_prompt

class MonitoringPlan(BaseModel):
    markdown_plan: str = None
    structured_plan: list[MonitoringInstruction] = None

class MonitoringFeedback(BaseModel):
    round_count: int = 0
    critic_approved: bool = False
    feedback_text: str = None

class AlertingRules(BaseModel):
    recommendation: str = None  # Full markdown response from agent
    generic_recommended_alerting_rules: str = None  # Original YAML
    az_compatible_recommended_alerting_rules: str = None  # Converted YAML


class Workflow(BaseModel):
    thread_id: str = None

    detected_workloads: dict[str, k8s_client.Workload] = None
    already_monitored_workloads: dict[str, k8s_client.Workload] = None

    detected_oss_workloads: dict[str, k8s_client.Workload] = None
    oss_detection_reasoning: str = None
    oss_detection_tool_calls: dict = None

    selected_oss_workload: k8s_client.Workload = None

    verified_oss_workload: k8s_client.Workload = None
    confirmed_to_plan: bool = None

    monitoring_plan_approval: bool = None
    monitoring_plan_feedback: MonitoringFeedback = None
    monitoring_plan: MonitoringPlan = None

    confirmed_to_plan: bool = None
    deployment_success: bool = None

    recommended_dashboards: dict[str, int] = None
    recommended_alerting_rules: AlertingRules = None

def detect_workloads(workflow: Workflow) -> dict[str, k8s_client.Workload]:
    """Detect workloads in the Kubernetes cluster and prune already-monitored ones."""
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
        
        total_detected = len(detected_workloads_dict)
        
        # Check for environment variable to enable/disable pruning
        enable_pruning = os.getenv("ENABLE_WORKLOAD_PRUNING", "true").lower() == "true"
        
        if not enable_pruning:
            logger.info("Workload pruning disabled via environment variable", extra={
                'component': 'ai_graphs',
                'operation': 'detect_workloads',
                'pruning_enabled': False
            })
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.info("Workload detection completed", extra={
                'component': 'ai_graphs',
                'operation': 'detect_workloads',
                'workflow_phase': 'workload-detection',
                'duration_ms': duration_ms,
                'workloads_detected': total_detected,
                'pruning_enabled': False
            })
            
            print_utils.print_workload_list("Detected Workloads", detected_workloads_dict)
            return {"detected_workloads": detected_workloads_dict, "already_monitored_workloads": {}}
        
        # Import helm utilities and prune already-monitored workloads
        try:
            from ai.utils.helm_utils import get_release_name_set, is_workload_monitored
            
            # Get current Helm releases once for efficiency
            logger.debug("Fetching current Helm releases for workload pruning")
            release_names = get_release_name_set()
            
            if not release_names:
                logger.warning("No Helm releases found or helm unavailable, skipping workload pruning", extra={
                    'component': 'ai_graphs',
                    'operation': 'detect_workloads',
                    'helm_available': False
                })
                duration_ms = round((time.time() - start_time) * 1000, 2)
                logger.info("Workload detection completed", extra={
                    'component': 'ai_graphs',
                    'operation': 'detect_workloads',
                    'workflow_phase': 'workload-detection',
                    'duration_ms': duration_ms,
                    'workloads_detected': total_detected,
                    'pruning_enabled': False,
                    'helm_available': False
                })
                
                print_utils.print_workload_list("Detected Workloads", detected_workloads_dict)
                return {"detected_workloads": detected_workloads_dict, "already_monitored_workloads": {}}
            
            # Separate workloads into monitored and unmonitored
            already_monitored = {}
            remaining_workloads = {}
            
            for key, workload in detected_workloads_dict.items():
                if is_workload_monitored(workload.name, workload.namespace, release_names):
                    already_monitored[key] = workload
                else:
                    remaining_workloads[key] = workload
            
            # Log pruning results
            monitored_count = len(already_monitored)
            remaining_count = len(remaining_workloads)
            
            logger.info("Workload pruning completed", extra={
                'component': 'ai_graphs',
                'operation': 'detect_workloads_prune',
                'total_detected': total_detected,
                'already_monitored': monitored_count,
                'remaining_unmonitored': remaining_count,
                'pruning_enabled': True,
                'helm_releases_found': len(release_names)
            })
            
            if monitored_count > 0:
                monitored_names = [w.name for w in already_monitored.values()]
                logger.info(f"Pruned {monitored_count} already-monitored workloads: {monitored_names}", extra={
                    'component': 'ai_graphs',
                    'operation': 'detect_workloads_prune',
                    'monitored_workloads': monitored_names
                })
                
        except ImportError as e:
            logger.warning(f"Helm utilities not available, skipping workload pruning: {e}", extra={
                'component': 'ai_graphs',
                'operation': 'detect_workloads',
                'error': 'helm_utils_import_error'
            })
            remaining_workloads = detected_workloads_dict
            already_monitored = {}
            
        except Exception as e:
            logger.warning(f"Workload pruning failed, proceeding without pruning: {e}", extra={
                'component': 'ai_graphs',
                'operation': 'detect_workloads',
                'error': 'pruning_error'
            })
            remaining_workloads = detected_workloads_dict
            already_monitored = {}

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Workload detection completed", extra={
            'component': 'ai_graphs',
            'operation': 'detect_workloads',
            'workflow_phase': 'workload-detection',
            'duration_ms': duration_ms,
            'total_detected': total_detected,
            'workloads_remaining': len(remaining_workloads),
            'workloads_already_monitored': len(already_monitored)
        })
        
        # Print remaining workloads (the ones that need monitoring)
        print_utils.print_workload_list("Detected Workloads (Unmonitored)", remaining_workloads)
        
        # Also print already-monitored workloads if any
        if already_monitored:
            print_utils.print_workload_list("Already-Monitored Workloads (Skipped)", already_monitored, "📊")
        
        return {
            "detected_workloads": remaining_workloads,
            "already_monitored_workloads": already_monitored
        }
        
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
            tool_calls = agent_utils.AgentManager.get_agent_tool_calls(response)
            if response_content:
                printer.out(response_content)
            if tool_calls:
                printer.out(tool_calls)
            workflow.oss_detection_reasoning = response_content
            workflow.oss_detection_tool_calls = tool_calls

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
    
    # Create a display-friendly structure for the interrupt
    # Keys are still original workload names, but we display pretty names
    workload_choices = {}
    for workload_key, workload in workflow.detected_oss_workloads.items():
        pretty_name = getattr(workload, 'pretty_name', workload.name)
        workload_choices[workload_key] = {
            "pretty_name": pretty_name,
            "service_name": workload.name,
            "namespace": workload.namespace,
            "service_type": workload.service_type
        }
    print("Already monitored workloads:", workflow.already_monitored_workloads)
    selected_workload_key = interrupt({"detected_oss_workloads": workload_choices, "already_monitored_workloads": workflow.already_monitored_workloads})

    if not selected_workload_key:
        logger.warning("No workload selected by user", extra={
            'component': 'ai_graphs',
            'operation': 'select_oss_workloads',
            'workflow_phase': 'workload-selection'
        })
        return {"selected_oss_workload": None}

    # Since we're selecting only one workload, get the first one from the list
    if isinstance(selected_workload_key, list) and len(selected_workload_key) > 0:
        selected_workload_key = selected_workload_key[0]
    
    selected_oss_workload = workflow.detected_oss_workloads.get(selected_workload_key)
    
    if selected_oss_workload:
        if hasattr(selected_oss_workload, 'pretty_name') and selected_oss_workload.pretty_name:
            printer.success(f"✅ Selected OSS Workload: {selected_oss_workload.pretty_name} ({selected_oss_workload.name})")
        else:
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

    # Get display name for logging
    display_name = workload.pretty_name if hasattr(workload, 'pretty_name') and workload.pretty_name else workload.name

    # Log plan generation start (system event)
    logger.info("Monitoring plan generation started", extra={
        'component': 'ai_graphs',
        'operation': 'generate_monitoring_deployment_plan',
        'workflow_phase': 'monitoring-plan-generation',
        'workload_name': workload.name,
        'pretty_name': getattr(workload, 'pretty_name', None),
        'is_improvement': is_improvement,
        'round_number': round_number
    })

    message = "Improving" if is_improvement else "Generating"
    printer.info(
        f"{message} monitoring deployment plan for {display_name}"
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
        model=models.llm_5,
        tools=[tools.get_chart_yaml_version, tools.get_values_yaml_formatted, tools.get_chart_readme, tools.search_values_keys],
        agent_prompt=prompts.NEW_MONITORING_PLAN_GENERATION_PROMPT
    )
    
    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        tool_calls = agent_utils.AgentManager.get_agent_tool_calls(response)
        printer.out(tool_calls)
        if response_content:
            monitoring_plan = MonitoringPlan(markdown_plan=response_content)
            printer.success(f"Generated monitoring plan for {display_name}")
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
    
    # Generate expected deterministic release name for validation
    from ai.utils.exporter_naming import create_exporter_release_name, get_exporter_name_for_workload
    workload = workflow.verified_oss_workload
    exporter_name = get_exporter_name_for_workload(workload.name)
    expected_release_name = create_exporter_release_name(exporter_name, workload.name, workload.namespace)
    
    # Create approval tool
    approval_result = {"approved": False, "feedback": "", "issues": []}
    approve_plan_tool = tools.create_plan_approval_tool(approval_result)
    
    # Build enhanced system prompt with workload context and exporter information
    enhanced_system_prompt = build_enhanced_evaluator_prompt(workflow.verified_oss_workload, exporter_name)
    
    # Prepare the evaluation prompt (focused only on the plan)
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
    
    CRITICAL VALIDATION REQUIREMENT:
    The plan MUST use this exact Helm release name: {expected_release_name}
    If the plan uses any other release name, it MUST be rejected with feedback to use the correct deterministic name.
    
    This is evaluation round {feedback.round_count} of {MAX_EVALUATION_ROUNDS}. 
    Provide comprehensive feedback and use the approve_plan tool to make your final decision.
    Use the available tools to cross-reference the plan against the official Helm chart documentation.
    
    Remember: You MUST call approve_plan() with your final decision after evaluation.
    """

    # Run the critic agent with enhanced context and tools
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=evaluation_prompt,
        model=models.llm_o3,
        tools=[tools.get_values_yaml, tools.get_chart_readme, tools.get_values_yaml_formatted, approve_plan_tool],
        agent_prompt=enhanced_system_prompt
    )
    
    if response:
        tool_calls = agent_utils.AgentManager.get_agent_tool_calls(response)
        printer.out(tool_calls)
        
        # Check if the approval tool was called
        if approval_result["feedback"]:
            feedback.feedback_text = approval_result["feedback"]
            feedback.critic_approved = approval_result["approved"]
            
            printer.banner("Critic Feedback")
            printer.out(feedback.feedback_text)
            
            if approval_result["issues"]:
                printer.out("\nCritical Issues Identified:")
                for issue in approval_result["issues"]:
                    printer.out(f"  • {issue}")
            printer.banner("Critic Feedback")

            status_message = "✅ Monitoring plan approved by critic!" if feedback.critic_approved else "❌ Monitoring plan needs improvement."
            printer.success(status_message) if feedback.critic_approved else printer.warning(status_message)
        else:
            # Fallback if tool wasn't called - but still try to get text feedback
            response_content = agent_utils.AgentManager.get_agent_response_content(response)
            feedback.critic_approved = False  # Default to not approved if tool wasn't used
            feedback.feedback_text = response_content or "Critic failed to use approval tool properly"
            printer.warning("Critic did not use the approval tool. Defaulting to rejection.")
            printer.out(feedback.feedback_text)
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
        model=models.llm_4o,
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

def reccomend_alerting_rules(workflow: Workflow) -> dict[str, AlertingRules]:
    """Recommend Prometheus alerting rules based on the structured monitoring plan."""
    if not workflow.monitoring_plan or not workflow.monitoring_plan.structured_plan:
        printer.error("No structured monitoring plan found to recommend alerting rules.")
        return {"recommended_alerting_rules": None}

    # Add interrupt to allow API query for alerting rule recommendations
    get_recommendations = interrupt({
        "message": "Ready to generate alerting rules recommendations. Call the API endpoint to proceed.",
        "workload_name": workflow.verified_oss_workload.name if workflow.verified_oss_workload else "Unknown",
        "monitoring_plan": workflow.monitoring_plan.markdown_plan
    })

    # If user chooses not to get recommendations, return None
    if not get_recommendations:
        printer.info("Alerting rules recommendations skipped.")
        return {"recommended_alerting_rules": None}

    analysis_prompt = f"""You need to recommend Prometheus alerting rules based on the monitoring plan for {workflow.verified_oss_workload.name}.

    Here is the monitoring plan in markdown format:
    {workflow.monitoring_plan.markdown_plan}

    """
    
    recommended_alerting_rules = {}
    add_alerting_rules = tools.create_add_alerting_rules_tool(recommended_alerting_rules)
    
    # Include the new awesome-prometheus-alerts tools
    response, _ = agent_utils.AgentManager.create_and_run_agent(
        prompt=analysis_prompt,
        model=models.llm_41,
        tools=[
            tools.get_awesome_rule_index,
            tools.get_awesome_rule, 
            add_alerting_rules
        ],
        agent_prompt=prompts.FIND_ALERTING_RULES_PROMPT
    )
    
    if response:
        response_content = agent_utils.AgentManager.get_agent_response_content(response)
        printer.out(response_content)
        tool_calls = agent_utils.AgentManager.get_agent_tool_calls(response)
        printer.out(tool_calls)
        
        # Get the YAML content from the tool
        generic_yaml = recommended_alerting_rules.get("yaml_content", "")
        printer.out(generic_yaml)
        
        if response_content and generic_yaml:
            printer.success("Recommended alerting rules generated successfully.")
            printer.out(response_content)  # Still print the explanation
            
            # Convert to Azure format
            printer.info("Converting alerting rules to Azure Managed Prometheus format...")
            az_compatible_yaml = tools.convert_to_azure_prom_rules(generic_yaml)
            
            if az_compatible_yaml:
                printer.success("Successfully converted to Azure Managed Prometheus format.")
            else:
                printer.warning("Azure conversion failed. Using generic format with conversion instructions.")
            
            # Create the AlertingRules object
            alerting_rules = AlertingRules(
                recommendation=response_content,
                generic_recommended_alerting_rules=generic_yaml,
                az_compatible_recommended_alerting_rules=az_compatible_yaml
            )
            
            print(f"Recommended Alerting Rules: {alerting_rules}")
            return {"recommended_alerting_rules": alerting_rules}
        else:
            printer.warning("Agent response was empty, no alerting rules recommended.")
    
    return {"recommended_alerting_rules": None}

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
    builder.add_node("reccomend_alerting_rules", reccomend_alerting_rules)

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
    builder.add_edge("reccomend_dashboards", "reccomend_alerting_rules")
    builder.add_edge("reccomend_alerting_rules", END)

    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    return graph


# Don't create a global graph - create a new one for each workflow
def get_graph():
    """Get a new graph instance for each workflow to avoid thread conflicts"""
    return build_graph()
