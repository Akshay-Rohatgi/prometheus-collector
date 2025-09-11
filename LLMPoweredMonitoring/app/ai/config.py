"""Configuration values for the AI module."""
import os
from dotenv import load_dotenv

load_dotenv()

# Kubernetes configuration
K8S_CONFIG_PATH = ""

# Workflow configuration
MAX_EVALUATION_ROUNDS = 2
DEFAULT_EMOJI = "🔨"
OSS_WORKLOAD_EMOJI = "🔍"

# Agent configuration
DEFAULT_MESSAGE_INDEX = 1  # Default index for extracting agent message content

# Azure OpenAI Model Configuration
AZURE_OPENAI_MODELS = {
    "o3": {
        "deployment": os.getenv("AZURE_DEPLOYMENT_O3", "o3"),
        "endpoint": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_KEY")
    },
    "gpt-4o": {
        "deployment": os.getenv("AZURE_DEPLOYMENT_4O", "gpt-4o"),
        "endpoint":os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_KEY"),
        "temperature": float(os.getenv("AZURE_TEMPERATURE_4O", "0.3"))
    },
    "gpt-4.1": {
        "deployment": os.getenv("AZURE_DEPLOYMENT_41", "gpt-4.1"),
        "endpoint": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_KEY"),
        "temperature": float(os.getenv("AZURE_TEMPERATURE_41", "0.3"))
    },
    "gpt-5": {
        "deployment": os.getenv("AZURE_DEPLOYMENT_5", "gpt-5"),
        "endpoint": os.getenv("OPENAI_ENDPOINT"),
        "api_key": os.getenv("OPENAI_KEY"),
        "reasoning_effort": os.getenv("AZURE_REASONING_EFFORT_5", "minimal")
    }
}

# API Version
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-12-01-preview")