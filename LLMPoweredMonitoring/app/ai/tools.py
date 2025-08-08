import k8s.client
from .utils import gh_utils
from .instructions import KubectlInstruction, HelmInstruction, CreateFileInstruction, OtherInstruction
import re
from printer import printer
from typing import Dict
from mistletoe import Document
from mistletoe.markdown_renderer import MarkdownRenderer
import threading

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
    def add_oss_workload(workload_name: str) -> str:
        """Add a workload name to the detected OSS workloads list."""
        detected_oss_workload_names.append(workload_name.lower())
        return f"Added {workload_name} to the detected OSS workloads list"
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

def _strip_sections_by_header(content: str, banned=("optional", "references")) -> str:
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
    workload_info = f"""
    Workload Information (Service):
    - Name: {workload.name}
    - Namespace: {workload.namespace}
    - Metadata Name: {workload.metadata_name}
    - Labels: {workload.metadata_labels}
    - Service Type: {workload.service_type}
    - Service Ports: {workload.service_ports}
    - Service Annotations: {workload.service_annotations}
    - Is OSS: {workload.is_oss}
    """

    return f"""Please generate a comprehensive monitoring deployment plan for the following workload as per your instructions:

    {workload_info}
    """