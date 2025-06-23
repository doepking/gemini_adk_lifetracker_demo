from google.adk.agents import LlmAgent
from .prompt import VISIONARY_PROMPT
from ...shared_libraries import constants

visionary_agent = LlmAgent(
    name="Visionary",
    model=constants.MODEL,
    description="A visionary agent that provides creative and forward-thinking insights.",
    instruction=VISIONARY_PROMPT,
    output_key="visionary_insights",
    disallow_transfer_to_parent=True,
)
