import os
from pathlib import Path

# Get the directory containing this file
current_dir = Path(__file__).parent

def load_prompt(filename: str) -> str:
    """Load a prompt from a markdown file."""
    prompt_path = current_dir / "prompts" / filename
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    except Exception as e:
        raise Exception(f"Error loading prompt from {prompt_path}: {str(e)}")

# Load all prompts
# OSS_DETECTION_PROMPT = load_prompt("oss_detection.md")
NEW_OSS_DETECTION_PROMPT = load_prompt("new_oss_detection.md")
# MONITORING_PLAN_OPTIMIZER_PROMPT = load_prompt("monitoring_plan_optimizer.md")
NEW_MONITORING_PLAN_GENERATION_PROMPT = load_prompt("new_monitoring_plan_generation.md")
MONITORING_PLAN_EVALUATOR_PROMPT = load_prompt("monitoring_plan_evaluator.md")
STRUCTURE_MONITORING_PLAN_PROMPT = load_prompt("structure_monitoring_plan.md")
FIND_GRAFANA_DASHBOARD_PROMPT = load_prompt("find_grafana_dashboard.md")