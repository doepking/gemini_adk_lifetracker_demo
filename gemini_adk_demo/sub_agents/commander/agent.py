from google.adk.agents import LlmAgent
from .prompt import COMMANDER_PROMPT
from ...shared_libraries import constants

commander_agent = LlmAgent(
    name="Commander",
    model=constants.MODEL,
    description="A commander agent that provides strategic and decisive action plans.",
    instruction=COMMANDER_PROMPT,
    output_key="commander_insights",
    disallow_transfer_to_parent=True,
)
