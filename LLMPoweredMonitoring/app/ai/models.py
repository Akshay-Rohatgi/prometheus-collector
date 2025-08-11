from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()
llm_4o_mini = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",
    api_version="2024-12-01-preview",
    azure_endpoint="https://rashmi-openai.openai.azure.com/",
    api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY")
)

llm_4o = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_version="2024-12-01-preview",
    temperature=0.3,
    azure_endpoint="https://rashmi-openai.openai.azure.com/",
    api_key=os.getenv("RASHMI_AZURE_OPENAI_API_KEY")
)

llm_5_mini = AzureChatOpenAI(
    azure_deployment="gpt-5-mini",
    api_version="2024-12-01-preview",
    azure_endpoint="https://t-arohatgi-5211-resource.cognitiveservices.azure.com/",
    api_key=os.getenv("AKSHAY_AZURE_OPENAI_API_KEY")
)