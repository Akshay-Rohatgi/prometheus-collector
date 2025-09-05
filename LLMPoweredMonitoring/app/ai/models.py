from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
llm_o3 = AzureChatOpenAI(
    azure_deployment="o3",
    api_version="2024-12-01-preview",
    azure_endpoint="https://rashmi-openai.openai.azure.com/",
    api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
)

llm_4o = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_version="2024-12-01-preview",
    temperature=0.3,
    azure_endpoint="https://rashmi-openai.openai.azure.com/",
    api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
)

llm_41 = AzureChatOpenAI(
    azure_deployment="gpt-4.1",
    api_version="2024-12-01-preview",
    temperature=0.3,
    azure_endpoint="https://rashmi-openai.openai.azure.com/",
    api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
)

llm_5 = AzureChatOpenAI(
    azure_deployment="gpt-5",
    api_version="2024-12-01-preview",
    azure_endpoint="https://t-arohatgi-5211-resource.cognitiveservices.azure.com/",
    api_key=os.getenv("AKSHAY_AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_KEY"),
    reasoning_effort="minimal"
)