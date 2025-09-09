from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from .config import AZURE_OPENAI_MODELS, AZURE_API_VERSION

load_dotenv()

def create_azure_model(model_key: str) -> AzureChatOpenAI:
    """Create an Azure OpenAI model instance from configuration."""
    if model_key not in AZURE_OPENAI_MODELS:
        raise ValueError(f"Model '{model_key}' not found in configuration")
    
    config = AZURE_OPENAI_MODELS[model_key]
    
    # Base parameters
    params = {
        "azure_deployment": config["deployment"],
        "api_version": AZURE_API_VERSION,
        "azure_endpoint": config["endpoint"],
        "api_key": config["api_key"]
    }
    
    # Add optional parameters if they exist
    if "temperature" in config:
        params["temperature"] = config["temperature"]
    if "reasoning_effort" in config:
        params["reasoning_effort"] = config["reasoning_effort"]
    
    return AzureChatOpenAI(**params)

# Create model instances
llm_o3 = create_azure_model("o3")
llm_4o = create_azure_model("gpt-4o")
llm_41 = create_azure_model("gpt-4.1")
llm_5 = create_azure_model("gpt-5")