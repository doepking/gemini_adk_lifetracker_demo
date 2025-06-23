from . import core  # Initialize Vertex AI
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .shared_libraries import constants
from .sub_agents.visionary.agent import visionary_agent
from .sub_agents.architect.agent import architect_agent
from .sub_agents.commander.agent import commander_agent
from .sub_agents.judge.agent import judge_agent
from .tools.callbacks import (
    load_user_data,
    load_user_data_after_tool_callback,
    rate_limit_callback,
)
from .tools.log_entry import add_log_entry_tool
from .tools.task_manager import create_tasks_tool, update_tasks_tool, list_tasks_tool
from .tools.background_info import update_background_info_tool

insight_team_agent = ParallelAgent(
    name="InsightTeam",
    sub_agents=[
        visionary_agent,
        architect_agent,
        commander_agent,
    ],
    description="Runs the Visionary, Architect, and Commander agents in parallel.",
)

insights_engine_workflow = SequentialAgent(
    name="InsightsEngineWorkflow",
    sub_agents=[
        insight_team_agent,
        judge_agent,
    ],
    description="Executes the full insights engine workflow.",
)

router_agent = LlmAgent(
    name=constants.AGENT_NAME,
    model="gemini-2.5-flash", # or "gemini-2.5-flash-lite-preview-06-17"
    description=constants.DESCRIPTION,
    instruction=prompt.ROUTER_PROMPT,
    output_key="router_output",
    before_agent_callback=load_user_data,
    after_tool_callback=load_user_data_after_tool_callback,
    before_model_callback=rate_limit_callback,
    tools=[
        add_log_entry_tool,
        update_background_info_tool,
        create_tasks_tool,
        update_tasks_tool,
        list_tasks_tool,
        AgentTool(agent=insights_engine_workflow),
    ],
)

root_agent = router_agent
