import os
from google.adk.models.lite_llm import LiteLlm

MODEL = LiteLlm(
    model="openai/GLM-4.5-Air",
    api_base=os.environ.get("ZAI_BASE_URL"),
    api_key=os.environ.get("ZAI_API_KEY")
)
AGENT_NAME = "router_agent"
DESCRIPTION = "The master coordinator for the Life Tracker. It delegates tasks to a team of specialized agents."
