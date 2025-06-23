from google.adk.agents import LlmAgent
from .prompt import ARCHITECT_PROMPT
from ...shared_libraries import constants

architect_agent = LlmAgent(
    name="Architect",
    model=constants.MODEL,
    description="An architect agent that provides structured and well-designed plans.",
    instruction=ARCHITECT_PROMPT,
    output_key="architect_insights",
    disallow_transfer_to_parent=True,
)
