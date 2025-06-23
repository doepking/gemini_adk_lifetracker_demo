from google.adk.agents import LlmAgent
from ...tools import add_log_entry_tool
from ...tools.callbacks import load_user_data, after_tool_callback
from .prompt import LOG_ENTRY_PROMPT
from ...shared_libraries import constants


log_entry_agent = LlmAgent(
    name="log_entry_agent",
    model=constants.MODEL,
    description="Logs a user's text input after light cleaning.",
    instruction=LOG_ENTRY_PROMPT,
    output_key="log_entry_confirmation",
    before_agent_callback=load_user_data,
    after_tool_callback=after_tool_callback,
    tools=[add_log_entry_tool],
)
