from google.adk.agents import LlmAgent
from ...tools.task_manager import create_tasks_tool, update_tasks_tool, list_tasks_tool
from ...tools.callbacks import load_user_data, after_tool_callback
from .prompt import TASK_MANAGER_PROMPT
from ...shared_libraries import constants



task_manager_agent = LlmAgent(
    name="task_manager_agent",
    model=constants.MODEL,
    description="Manages tasks based on user input.",
    instruction=TASK_MANAGER_PROMPT,
    output_key="task_management_confirmation",
    before_agent_callback=load_user_data,
    after_tool_callback=after_tool_callback,
    tools=[create_tasks_tool, update_tasks_tool, list_tasks_tool],
)
