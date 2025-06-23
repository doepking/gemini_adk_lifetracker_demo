from google.adk.agents import LlmAgent
from ...tools import update_background_info_tool
from ...tools.callbacks import load_user_data, after_tool_callback
from .prompt import BACKGROUND_INFO_PROMPT
from ...shared_libraries import constants


background_info_agent = LlmAgent(
    name="background_info_agent",
    model=constants.MODEL,
    description="Manages the user's background information.",
    instruction=BACKGROUND_INFO_PROMPT,
    output_key="background_info_confirmation",
    before_agent_callback=load_user_data,
    after_tool_callback=after_tool_callback,
    tools=[update_background_info_tool],
)
