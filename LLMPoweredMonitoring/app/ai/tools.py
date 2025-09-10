import k8s.client
from .utils import gh_utils
from .instructions import KubectlInstruction, HelmInstruction, CreateFileInstruction, OtherInstruction
import re
from printer import printer
from typing import Dict, List
from mistletoe import Document
from mistletoe.markdown_renderer import MarkdownRenderer
import threading
import os
import glob
import yaml
import requests
import asyncio
from logs import get_logger, log_with_context

logger = get_logger(__name__)

# Constants
AWESOME_ALERTS_BASE_PATH = "/opt/awesome-prometheus-alerts/dist/rules"

# Global lock to serialize mistletoe usage (mistletoe is not thread-safe)
_MD_LOCK = threading.Lock()

# Regex to match markdown headers (e.g., #, ##, ### Title)
_SECTION_MATCH = re.compile(r'^(#{1,6})\s+(.*)$')


def _flatten_dict(data: dict, parent_key: str = '', separator: str = '.') -> dict:
    """Flatten a nested dictionary using dot notation."""
    items = []
    for key, value in data.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        if isinstance(value, dict):
            items.extend(_flatten_dict(value, new_key, separator).items())
        elif isinstance(value, list):
            # For lists, we'll just convert to string representation
            items.append((new_key, str(value)))
        else:
            items.append((new_key, value))
    return dict(items)

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

def get_values_yaml_formatted(exporter_name: str) -> dict:
    """Get the flattened key-value pairs from values.yaml for a prometheus exporter."""
    try:
        # Get GitHub client and repo
        github_client = gh_utils.get_github_client()
        repo = gh_utils.get_repo(github_client, "prometheus-community/helm-charts")
        
        # Get values.yaml content from the exporter directory
        chart_dir = f"charts/prometheus-{exporter_name}-exporter"
        try:
            directory_content = gh_utils.get_directory_content(repo, chart_dir)
            values_content = gh_utils.get_file_content_from_directory(repo, directory_content, "values.yaml")

            # Parse YAML and flatten to dot notation
            import yaml
            values_data = yaml.safe_load(values_content)
            flattened_values = _flatten_dict(values_data)
            
            return flattened_values
        except Exception as e:
            return {"error": f"Could not find values.yaml for prometheus-{exporter_name}-exporter: {str(e)}"}
    except Exception as e:
        return {"error": f"Error accessing GitHub repository: {str(e)}"}

def get_values_yaml(exporter_name: str) -> str:
    """Get the complete values.yaml content with comments preserved for a prometheus exporter."""
    printer.info(f"[tool-call] get_values_yaml({exporter_name})")
    try:
        # Get GitHub client and repo
        github_client = gh_utils.get_github_client()
        repo = gh_utils.get_repo(github_client, "prometheus-community/helm-charts")
        
        # Get values.yaml content from the exporter directory
        chart_dir = f"charts/prometheus-{exporter_name}-exporter"
        try:
            directory_content = gh_utils.get_directory_content(repo, chart_dir)
            values_content = gh_utils.get_file_content_from_directory(repo, directory_content, "values.yaml")
            return f"Complete values.yaml for prometheus-{exporter_name}-exporter:\n\n{values_content}"
        except Exception as e:
            return f"Could not find values.yaml for prometheus-{exporter_name}-exporter: {str(e)}"
    except Exception as e:
        return f"Error accessing GitHub repository: {str(e)}"

def get_chart_readme(exporter_name: str) -> str:
    """Get the README.md content for a prometheus exporter chart."""
    try:
        # Get GitHub client and repo
        github_client = gh_utils.get_github_client()
        repo = gh_utils.get_repo(github_client, "prometheus-community/helm-charts")
        
        # Get README.md content from the exporter directory
        chart_dir = f"charts/prometheus-{exporter_name}-exporter"
        try:
            directory_content = gh_utils.get_directory_content(repo, chart_dir)
            readme_content = gh_utils.get_file_content_from_directory(repo, directory_content, "README.md")
            
            return f"README for prometheus-{exporter_name}-exporter:\n\n{readme_content}"
        except Exception as e:
            return f"Could not find README.md for prometheus-{exporter_name}-exporter: {str(e)}"
    except Exception as e:
        return f"Error accessing GitHub repository: {str(e)}"

def search_values_keys(exporter_name: str, regex_pattern: str) -> dict:
    """Search for keys in values.yaml that match a regex pattern."""
    try:
        # Get the flattened values first
        values_dict = get_values_yaml_formatted(exporter_name)
        
        # Check if there was an error getting the values
        if "error" in values_dict:
            return values_dict
        
        # Compile the regex pattern
        try:
            pattern = re.compile(regex_pattern, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex pattern '{regex_pattern}': {str(e)}"}
        
        # Search for matching keys
        matching_keys = {}
        for key, value in values_dict.items():
            if pattern.search(key):
                matching_keys[key] = value
        
        return matching_keys
    except Exception as e:
        return {"error": f"Error searching values for prometheus-{exporter_name}-exporter: {str(e)}"}

def create_add_oss_workload_tool(detected_oss_workload_names: list) -> callable:
    """Create the add_oss_workload tool function."""
    def add_oss_workload(workload_name: str, pretty_workload_name: str) -> str:
        """Add a workload name to the detected OSS workloads list with a pretty name.
        
        Args:
            workload_name: The exact service name from Kubernetes (e.g., "kafka-brokers", "quickstart-es-default")
            pretty_workload_name: Human-readable name for the workload (e.g., "kafka", "elasticsearch", "nginx")
        """
        printer.info(f"[tool-call] Adding {workload_name} as '{pretty_workload_name}' to detected OSS workloads")
        detected_oss_workload_names.append({
            "workload_name": workload_name.lower(),
            "pretty_name": pretty_workload_name.lower()
        })
        logger.info(f"Adding {workload_name} as '{pretty_workload_name}' to detected OSS workloads", extra={
            'component': 'workflow',
            'operation': 'add_oss_workload',
            'workload_name': workload_name,
            'pretty_name': pretty_workload_name
        })
        return f"Added {workload_name} as OSS workload with pretty name '{pretty_workload_name}'"
    return add_oss_workload

def create_add_recommended_dashboard_tool(recommended_dashboards: dict) -> callable:
    """Create a function to add a recommended dashboard."""
    def add_recommended_dashboard(dashboard_name: str, dashboard_id: int) -> str:
        """Add a recommended Grafana dashboard to the list.
        
        Use this tool to recommend specific Grafana dashboards that would be useful for monitoring
        the workload based on the monitoring plan. Include the dashboard name and its ID.
        
        Args:
            dashboard_name: The name/title of the Grafana dashboard (e.g., "Kafka Exporter Overview")
            dashboard_id: The Grafana dashboard ID (e.g., 7589)
        
        Returns:
            Confirmation message that the dashboard was added
        """
        printer.info(f"[tool-call] Adding recommended dashboard: {dashboard_name} (ID: {dashboard_id})")
        logger.info(f"Adding recommended dashboard: {dashboard_name} (ID: {dashboard_id})", extra={
            'component': 'workflow',
            'operation': 'add_recommended_dashboard'
        })
        recommended_dashboards[dashboard_name] = dashboard_id
        return f"Added recommended dashboard: {dashboard_name} (ID: {dashboard_id})"
    return add_recommended_dashboard


def create_add_instruction(instruction_list: list) -> callable:
    """Create the add_instruction tool function."""
    def add_instruction(type: str, content: str, filename: str = None) -> str:
        """Add an instruction to the instruction list.
        
        Args:
            type: The type of instruction (e.g., 'kubectl', 'helm', 'create_file', 'other')
            content: The actual content of the instruction
            filename: Required for create_file type, the name of the file to create
        """
        printer.info(f"[tool-call] Adding instruction: {type} - {content}")
        logger.info(f"Adding instruction: {type} - {content}", extra={
            'component': 'workflow',
            'operation': 'add_instruction'
        })
        type_lower = type.lower()
        
        if type_lower == 'kubectl':
            instruction = KubectlInstruction(command=content)
        elif type_lower == 'helm':
            instruction = HelmInstruction(command=content)
        elif type_lower == 'create_file':
            if not filename:
                return "Error: filename is required for create_file instructions"
            instruction = CreateFileInstruction(filename=filename, content=content)
        else:
            instruction = OtherInstruction(description=type, content=content)
        
        printer.info(f"Adding instruction: {instruction}")
        instruction_list.append(instruction)
        return f"Added instruction: {instruction}"
    return add_instruction

def _strip_sections_by_header(content: str, banned=("optional", "references", "if needed")) -> str:
    """Remove sections whose header contains any banned keyword.

    Thread-safe and deterministic; does not rely on markdown parsers.
    """
    if not content:
        return content

    lines = content.splitlines()
    out = []
    skip = False
    skip_level = 0

    for raw in lines:
        line = raw.rstrip("\n")
        m = _SECTION_MATCH.match(line.strip())
        if m:
            level = len(m.group(1))
            title = m.group(2).strip().lower()

            # If we were skipping and hit a header at same or higher level, stop skipping
            if skip and level <= skip_level:
                skip = False
                skip_level = 0

            # If not skipping, decide whether to start skipping this section
            if not skip and any(b in title for b in banned):
                skip = True
                skip_level = level
                continue  # Do not include the banned header line itself

        if not skip:
            out.append(line)

    return "\n".join(out)

def preprocess_markdown(content) -> str:
    """Preprocess markdown in a thread-safe way.

    - First, remove banned sections via simple header-based filtering.
    - Then, optionally normalize via mistletoe under a global lock.
    - On any failure, fall back to the filtered text.
    """
    if not content:
        return content

    # 1) Deterministic, thread-safe filter (no parser involved)
    filtered = _strip_sections_by_header(content)

    # 2) Optional normalization guarded by a global lock (mistletoe is not thread-safe)
    try:
        with _MD_LOCK:
            doc = Document(filtered)
            renderer = MarkdownRenderer()
            return renderer.render(doc)
    except Exception as e:
        printer.warning(f"Markdown normalization failed ({e}); using filtered text")
        return filtered

def generate_workload_detection_analysis_prompt(workloads: dict[str, k8s.client.Workload]) -> str:
    analysis_prompt = """Please analyze the following Kubernetes workloads (services) and identify which ones are major, first-class OSS workloads suitable for Prometheus monitoring.

WORKLOADS TO ANALYZE:
"""
    
    for workload in workloads.values():
        analysis_prompt += f"""
workload_name: {workload.name}
Namespace: {workload.namespace}
Metadata Name: {workload.metadata_name}
Labels: {workload.metadata_labels}
Service Type: {workload.service_type}
Service Ports: {workload.service_ports}
Service Annotations: {workload.service_annotations}
---
"""

    analysis_prompt += """
For each workload you identify as a major OSS project (HIGH confidence), use the add_oss_workload tool to add it to the detected list.
"""

    return analysis_prompt

def generate_monitoring_plan_prompt(workload: k8s.client.Workload) -> str:
    from .utils.exporter_naming import create_exporter_release_name, get_exporter_name_for_workload
    
    pretty_name_info = ""
    if hasattr(workload, 'pretty_name') and workload.pretty_name:
        pretty_name_info = f"\n    - Pretty Name: {workload.pretty_name}"
    
    # Generate deterministic Helm release name
    exporter_name = get_exporter_name_for_workload(workload.name)
    release_name = create_exporter_release_name(exporter_name, workload.name, workload.namespace)
    
    workload_info = f"""
    Workload Information (Service):
    - Name: {workload.name}{pretty_name_info}
    - Namespace: {workload.namespace}
    - Metadata Name: {workload.metadata_name}
    - Labels: {workload.metadata_labels}
    - Service Type: {workload.service_type}
    - Service Ports: {workload.service_ports}
    - Service Annotations: {workload.service_annotations}
    - Is OSS: {workload.is_oss}
    """
    
    deterministic_naming_instruction = f"""
    
    CRITICAL: You MUST use this exact Helm release name (no variations allowed):
    Release Name: {release_name}
    
    All helm install commands MUST start with:
    helm install {release_name} prometheus-community/prometheus-{exporter_name}-exporter \\
    
    Do NOT use any other release name or invent variations. This deterministic naming enables 
    reliable detection of already-monitored workloads.
    """

    return f"""Please generate a comprehensive monitoring deployment plan for the following workload as per your instructions:

    {workload_info}
    {deterministic_naming_instruction}
    """


def create_add_alerting_rules_tool(alerting_rules_storage: dict) -> callable:
    """Create a function to add alerting rules."""
    def add_alerting_rules(yaml_content: str) -> str:
        """Add Prometheus alerting rules in YAML format.
        
        This tool should be used to provide the final Prometheus alerting rules configuration
        that will be deployed to monitor the workload. The rules should be in proper Prometheus
        YAML format and include appropriate alert conditions, thresholds, and severity levels.
        
        Args:
            yaml_content: Complete YAML content for Prometheus alerting rules
            
        Returns:
            Confirmation message that the rules were added
        """
        printer.info(f"[tool-call] Adding alerting rules YAML content (length: {len(yaml_content)} chars)")
        logger.info(f"Adding alerting rules YAML content", extra={
            'component': 'workflow',
            'operation': 'add_alerting_rules',
            'yaml_length': len(yaml_content)
        })
        alerting_rules_storage["yaml_content"] = yaml_content
        return f"Successfully added Prometheus alerting rules configuration ({len(yaml_content)} characters)"
    
    return add_alerting_rules

def create_plan_approval_tool(approval_result: dict) -> callable:
    """Create a tool for the critic to explicitly approve or reject monitoring plans."""
    def approve_plan(approved: bool, feedback: str, critical_issues: list = None) -> str:
        """
        Tool for critic to explicitly approve or reject a monitoring plan.
        
        This tool MUST be called at the end of your evaluation to make a final decision.
        Use this after you have thoroughly evaluated the monitoring plan against all criteria.
        
        Args:
            approved (bool): True if the plan is approved and ready for deployment, 
                           False if it needs improvement before deployment
            feedback (str): Detailed feedback explaining your decision, including specific 
                          issues found or confirmation that requirements are met
            critical_issues (list, optional): List of critical issues that must be fixed 
                                            if the plan is not approved. Each item should 
                                            be a clear, actionable issue description.
        
        Returns:
            Confirmation message about the approval decision
            
        Examples:
            - approve_plan(True, "Plan meets all Azure Managed Prometheus requirements...")
            - approve_plan(False, "Plan has critical issues that need addressing...", 
                         ["Missing apiVersion override for Azure", "Incorrect service URI format"])
        """
        approval_result["approved"] = approved
        approval_result["feedback"] = feedback
        approval_result["issues"] = critical_issues or []
        
        status = "APPROVED" if approved else "NEEDS IMPROVEMENT"
        issues_text = f" with {len(approval_result['issues'])} critical issues" if approval_result['issues'] else ""
        
        printer.info(f"[tool-call] Plan evaluation complete: {status}{issues_text}")
        logger.info(f"Plan approval decision made: {status}", extra={
            'component': 'workflow',
            'operation': 'approve_plan',
            'approved': approved,
            'critical_issues_count': len(approval_result['issues'])
        })
        
        return f"Plan evaluation complete: {status}"
    
    return approve_plan


def get_awesome_rule_index() -> List[str]:
    """Get the index of all available rule directories from awesome-prometheus-alerts.
    
    Returns a list of service names that have alerting rules available.
    This helps narrow down which services have pre-built alerting rules.
    
    Returns:
        List of directory names (service names) available in awesome-prometheus-alerts
    """
    printer.info("[tool-call] Getting awesome-prometheus-alerts rule index")
    logger.info("Getting awesome-prometheus-alerts rule index", extra={
        'component': 'ai_tools',
        'operation': 'get_awesome_rule_index'
    })
    
    try:
        if not os.path.exists(AWESOME_ALERTS_BASE_PATH):
            error_msg = "awesome-prometheus-alerts repository not found at /opt/awesome-prometheus-alerts. Please ensure it's cloned."
            logger.warning(error_msg, extra={
                'component': 'ai_tools',
                'operation': 'get_awesome_rule_index',
                'path_checked': AWESOME_ALERTS_BASE_PATH
            })
            return [f"Error: {error_msg}"]
        
        # Get all directories in the rules path
        directories = []
        for item in os.listdir(AWESOME_ALERTS_BASE_PATH):
            item_path = os.path.join(AWESOME_ALERTS_BASE_PATH, item)
            if os.path.isdir(item_path):
                directories.append(item)
        
        directories.sort()  # Sort alphabetically for consistency
        
        if not directories:
            logger.warning("No rule directories found in awesome-prometheus-alerts", extra={
                'component': 'ai_tools',
                'operation': 'get_awesome_rule_index',
                'path_checked': AWESOME_ALERTS_BASE_PATH
            })
            return ["No rule directories found in awesome-prometheus-alerts"]
        
        logger.info(f"Found {len(directories)} rule directories", extra={
            'component': 'ai_tools',
            'operation': 'get_awesome_rule_index',
            'directories_count': len(directories)
        })
        
        return directories
        
    except Exception as e:
        error_msg = f"Error reading awesome-prometheus-alerts index: {str(e)}"
        logger.error(error_msg, extra={
            'component': 'ai_tools',
            'operation': 'get_awesome_rule_index',
            'error': str(e)
        })
        return [error_msg]


def get_awesome_rule(service_name: str) -> Dict[str, str]:
    """Get all YAML rule files for a specific service from awesome-prometheus-alerts.
    
    Args:
        service_name: The service name (directory name) to get rules for
        
    Returns:
        Dictionary with yaml_file_name as key and yaml_content as value
    """
    printer.info(f"[tool-call] Getting awesome-prometheus-alerts rules for {service_name}")
    logger.info(f"Getting awesome-prometheus-alerts rules for service", extra={
        'component': 'ai_tools',
        'operation': 'get_awesome_rule',
        'service_name': service_name
    })
    
    try:
        service_path = os.path.join(AWESOME_ALERTS_BASE_PATH, service_name)
        
        if not os.path.exists(service_path):
            error_msg = f"Service '{service_name}' not found in awesome-prometheus-alerts. Use get_awesome_rule_index() to see available services."
            logger.warning(error_msg, extra={
                'component': 'ai_tools',
                'operation': 'get_awesome_rule',
                'service_name': service_name,
                'path_checked': service_path
            })
            return {"error": error_msg}
        
        if not os.path.isdir(service_path):
            error_msg = f"'{service_name}' exists but is not a directory"
            logger.warning(error_msg, extra={
                'component': 'ai_tools',
                'operation': 'get_awesome_rule',
                'service_name': service_name,
                'path_checked': service_path
            })
            return {"error": error_msg}
        
        # Find all .yml and .yaml files in the service directory
        yaml_files = glob.glob(os.path.join(service_path, "*.yml")) + glob.glob(os.path.join(service_path, "*.yaml"))
        
        if not yaml_files:
            error_msg = f"No YAML files found for service '{service_name}'"
            logger.warning(error_msg, extra={
                'component': 'ai_tools',
                'operation': 'get_awesome_rule',
                'service_name': service_name,
                'yaml_files_count': 0
            })
            return {"error": error_msg}
        
        rule_contents = {}
        successful_files = 0
        
        for yaml_file_path in yaml_files:
            try:
                with open(yaml_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Validate it's actually valid YAML
                try:
                    yaml.safe_load(content)  # Just to validate, we return raw content
                    successful_files += 1
                except yaml.YAMLError as ye:
                    logger.warning(f"YAML parse error in {yaml_file_path}: {str(ye)}", extra={
                        'component': 'ai_tools',
                        'operation': 'get_awesome_rule',
                        'service_name': service_name,
                        'file_path': yaml_file_path,
                        'yaml_error': str(ye)
                    })
                    rule_contents[os.path.basename(yaml_file_path)] = f"# YAML Parse Error: {str(ye)}\n{content}"
                    continue
                
                rule_contents[os.path.basename(yaml_file_path)] = content
                
            except Exception as e:
                logger.error(f"Error reading file {yaml_file_path}: {str(e)}", extra={
                    'component': 'ai_tools',
                    'operation': 'get_awesome_rule',
                    'service_name': service_name,
                    'file_path': yaml_file_path,
                    'error': str(e)
                })
                rule_contents[os.path.basename(yaml_file_path)] = f"# Error reading file: {str(e)}"
        
        if not rule_contents:
            error_msg = f"Could not read any YAML files for service '{service_name}'"
            logger.warning(error_msg, extra={
                'component': 'ai_tools',
                'operation': 'get_awesome_rule',
                'service_name': service_name
            })
            return {"error": error_msg}
        
        logger.info(f"Successfully loaded {successful_files}/{len(yaml_files)} YAML files for {service_name}", extra={
            'component': 'ai_tools',
            'operation': 'get_awesome_rule',
            'service_name': service_name,
            'successful_files': successful_files,
            'total_files': len(yaml_files)
        })
            
        return rule_contents
        
    except Exception as e:
        error_msg = f"Error accessing awesome-prometheus-alerts rules for '{service_name}': {str(e)}"
        logger.error(error_msg, extra={
            'component': 'ai_tools',
            'operation': 'get_awesome_rule',
            'service_name': service_name,
            'error': str(e)
        })
        return {"error": error_msg}

def fix_parameter_references(arm_template):
    """Fix parameter references in ARM template by modifying the JSON structure directly."""
    from logs import get_logger
    
    logger = get_logger(__name__)
    
    try:
        if 'parameters' in arm_template:
            # Fix location parameter default value
            if 'location' in arm_template['parameters']:
                if arm_template['parameters']['location'].get('defaultValue') != '[resourceGroup().location]':
                    arm_template['parameters']['location']['defaultValue'] = '[resourceGroup().location]'

            # # set actionGroupId 
            # if 'actionGroupId' in arm_template['parameters']:
            #     arm_template['parameters']['actionGroupId']['value'] = "/subscriptions/<subscription_id>/resourcegroups/<resource_group_name>/providers/microsoft.insights/actiongroups/<action_group_name>"
        
            # # set clusterName
            # if 'clusterName' in arm_template['parameters']:
            #     arm_template['parameters']['clusterName']['value'] = "<cluster_name>"

            # # set azureMonitorWorkspace
            # if 'azureMonitorWorkspace' in arm_template['parameters']:
            #     arm_template['parameters']['azureMonitorWorkspace']['value'] = "/subscriptions/<subscription_id>/resourcegroups/<resource_group_name>/providers/microsoft.monitor/accounts/<azure_monitor_workspace_name>"

        # Process each resource
        for resource in arm_template.get('resources', []):
            # Fix location at resource level
            if resource.get('location') != "[parameters('location')]":
                resource['location'] = "[parameters('location')]"
            
            # Fix properties section
            properties = resource.get('properties', {})
            
            # Fix clusterName
            if properties.get('clusterName') != "[parameters('clusterName')]":
                properties['clusterName'] = "[parameters('clusterName')]"
            
            # Fix scopes array
            if 'scopes' in properties:
                scopes = properties['scopes']
                if not isinstance(scopes, list) or not scopes or scopes[0] != "[parameters('azureMonitorWorkspace')]":
                    properties['scopes'] = ["[parameters('azureMonitorWorkspace')]"]
            
            # Fix rules array
            for rule in properties.get('rules', []):
                # Fix actions in alerting rules
                for action in rule.get('actions', []):
                    if action.get('actionGroupId') != "[parameters('actionGroupId')]":
                        action['actionGroupId'] = "[parameters('actionGroupId')]"
        
        logger.info("Fixed parameter references in ARM template", extra={
            'component': 'ai_tools',
            'operation': 'fix_parameter_references',
            'resources_processed': len(arm_template.get('resources', []))
        })
        
        return arm_template
    except Exception as e:
        printer.out("[x] Error fixing parameter references")
        logger.error(f"Error fixing parameter references: {e}", extra={
            'component': 'ai_tools',
            'operation': 'fix_parameter_references',
            'error': str(e)
        })
        # Return original template if fixing fails
        return arm_template


def _sanitize_yaml_templates(yaml_content: str) -> str:
    """
    Quote annotation values that contain template braces like {{ ... }} to avoid YAML parse errors.
    Only affects scalar lines under 'annotations:' blocks that are not already quoted or block scalars.
    """
    lines = yaml_content.splitlines()
    out = []
    in_annotations = False
    annotations_indent = None

    for line in lines:
        # Detect entering an annotations block
        m_ann = re.match(r'^(\s*)annotations\s*:\s*$', line)
        if m_ann:
            in_annotations = True
            annotations_indent = len(m_ann.group(1))
            out.append(line)
            continue

        if in_annotations:
            # Determine whether we've left the annotations block
            current_indent = len(line) - len(line.lstrip(' '))
            if current_indent <= (annotations_indent or 0):
                in_annotations = False
                annotations_indent = None
                # fall through to append unmodified

            else:
                # Inside annotations: try to quote unquoted scalar values with templates
                # Skip comments or list items
                if re.match(r'^\s*#', line) or re.match(r'^\s*-\s', line):
                    out.append(line)
                    continue

                # key: value
                m_kv = re.match(r'^(\s*)([^:\'"]+?)\s*:\s*(.*)$', line)
                if m_kv:
                    pre, key, value = m_kv.groups()
                    # If empty or already quoted or block scalar, leave as-is
                    if value == '' or value[:1] in ['"', "'"] or value[:1] in ['|', '>']:
                        out.append(line)
                        continue

                    # If contains mustache templates, quote it
                    if '{{' in value and '}}' in value:
                        # Use single quotes for YAML and escape internal single quotes by doubling
                        safe = value.replace("'", "''")
                        out.append(f"{pre}{key}: '{safe}'")
                        continue

        out.append(line)

    return '\n'.join(out)


def fix_yaml_content(yaml_content: str) -> str:
    """
    Fix YAML content to ensure:
    1. No multiline descriptions (convert to single line)
    2. No more than 20 alert rules total
    3. "for" durations are not greater than 1m
    4. Valid YAML structure
    """
    import re
    from printer import printer
    from logs import get_logger
    
    logger = get_logger(__name__)
    
    # Pre-sanitize to avoid YAML parse errors (e.g., mapping values are not allowed here)
    sanitized_content = _sanitize_yaml_templates(yaml_content)
    
    try:
        # Parse the YAML content
        data = yaml.safe_load(sanitized_content)
        
        if not data or 'groups' not in data:
            printer.out("⚠️  No valid groups found in YAML")
            return sanitized_content
        
        total_rules = 0
        
        # Process each group
        for group in data['groups']:
            if 'rules' not in group:
                continue
                
            rules_to_keep = []
            
            for rule in group['rules']:
                # Count total rules
                total_rules += 1
                
                # Fix "for" duration if it exists and is greater than 1m
                if 'for' in rule:
                    for_duration = rule['for']
                    # Parse duration (e.g., "5m", "2h", "30s")
                    duration_match = re.match(r'^(\d+)([smhd])$', str(for_duration))
                    if duration_match:
                        value, unit = duration_match.groups()
                        value = int(value)
                        
                        # Convert to seconds for comparison
                        if unit == 's':
                            seconds = value
                        elif unit == 'm':
                            seconds = value * 60
                        elif unit == 'h':
                            seconds = value * 3600
                        elif unit == 'd':
                            seconds = value * 86400
                        else:
                            seconds = 60  # Default to 1m if unknown unit
                        
                        # If greater than 1 minute (60 seconds), set to 1m
                        if seconds > 60:
                            rule['for'] = '1m'
                            printer.out(f"🔧 Fixed 'for' duration from {for_duration} to 1m for alert: {rule.get('alert', 'unknown')}")
                
                # Fix multiline descriptions in annotations
                if 'annotations' in rule and isinstance(rule['annotations'], dict):
                    for key, value in list(rule['annotations'].items()):
                        if isinstance(value, str) and '\n' in value:
                            # Convert multiline to single line, replacing newlines with spaces
                            single_line = re.sub(r'\s*\n\s*', ' ', value.strip())
                            rule['annotations'][key] = single_line
                            printer.out(f"🔧 Fixed multiline {key} for alert: {rule.get('alert', 'unknown')}")
                
                rules_to_keep.append(rule)
            
            # Limit rules to 20 maximum
            if len(rules_to_keep) > 20:
                printer.out(f"⚠️  Limiting rules from {len(rules_to_keep)} to 20 (keeping most critical)")
                # Keep only first 20 rules (assuming they're ordered by importance)
                rules_to_keep = rules_to_keep[:20]
                total_rules = 20
            
            group['rules'] = rules_to_keep
        
        # Log summary
        printer.out(f"✅ YAML validation complete: {total_rules} rules processed")
        
        # Convert back to YAML string
        fixed_yaml = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return fixed_yaml
        
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error: {e}", extra={
            'component': 'ai_tools',
            'operation': 'fix_yaml_content',
            'error': str(e)
        })
        printer.out(f"❌ YAML parsing error (using sanitized content as fallback): {e}")
        # Fall back to sanitized content so the downstream converter can still try
        return sanitized_content
        
    except Exception as e:
        logger.error(f"Error fixing YAML content: {e}", extra={
            'component': 'ai_tools',
            'operation': 'fix_yaml_content',
            'error': str(e)
        })
        printer.out(f"❌ Error fixing YAML content: {e}")
        return sanitized_content  # Return sanitized YAML if any error occurs

def convert_to_azure_prom_rules(yaml_content: str) -> str:
    """Convert generic Prometheus rules to Azure-compatible format."""
    import subprocess
    import json
    import os
    from printer import printer
    from logs import get_logger
    
    logger = get_logger(__name__)
    
    # Fix YAML content before processing
    printer.out("🔧 Fixing YAML content...")
    fixed_yaml_content = fix_yaml_content(yaml_content)
    
    # write to temporary file /tmp/temp.yaml - use fixed content
    if os.path.exists("/tmp/temp.yaml"):
        os.remove("/tmp/temp.yaml")
    with open("/tmp/temp.yaml", "w") as f:
        f.write(fixed_yaml_content)  # Write fixed YAML content
    
    try:
        # Copy current environment and run converter
        import copy
        env = copy.deepcopy(os.environ)
        
        # Run: az-prom-rules-converter /tmp/temp.yaml from /tmp directory
        result = subprocess.run(
            ['az-prom-rules-converter', 'temp.yaml'],
            text=True,
            capture_output=True,
            check=True,
            timeout=30,  # 30 second timeout
            cwd='/tmp',  # Run from /tmp directory
            env=env  # Pass environment variables
        )
        print(result.stdout.strip())
        os.remove("/tmp/temp.yaml")
        
        # Parse the JSON output and fix parameter references
        try:
            arm_template = json.loads(result.stdout.strip())
            
            # Apply our fixes to replace empty strings with proper parameter references
            printer.out("Applying parameter reference fixes...")
            # arm_template = fix_parameter_references(arm_template)
            
            # Convert back to JSON string
            fixed_output = json.dumps(arm_template, indent=2)
            printer.out("✅ ARM template parameter references fixed successfully!")
            return fixed_output
            
        except json.JSONDecodeError:
            # Fallback to original output if JSON parsing fails
            printer.out("JSON parsing failed, returning original output:")
            printer.out(result.stdout.strip())
            return result.stdout.strip()
            
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Azure conversion failed: {e}", extra={
            'component': 'ai_tools',
            'operation': 'convert_to_azure_prom_rules',
            'error': str(e)
        })
        if os.path.exists("/tmp/temp.yaml"):
            os.remove("/tmp/temp.yaml")
        return None


async def fetch_dashboard_from_source(dashboard_id: str) -> dict:
    """Fetch dashboard JSON from grafana.com API."""
    try:
        url = f"https://grafana.com/api/dashboards/{dashboard_id}/revisions/latest/download"

        # Run the blocking request in a thread pool to keep it async
        response = await asyncio.to_thread(requests.get, url, timeout=10)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Failed to fetch dashboard {dashboard_id}: HTTP {response.status_code}")
            return None
    except requests.RequestException as e:
        logger.error(f"Network error fetching dashboard {dashboard_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching dashboard {dashboard_id}: {e}")
        return None

