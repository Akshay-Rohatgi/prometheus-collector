from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv

load_dotenv()
llm_4o_mini = AzureChatOpenAI(
    azure_deployment="gpt-4o-mini",
    api_version="2024-12-01-preview",
)

llm_41 = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_version="2024-12-01-preview",
)