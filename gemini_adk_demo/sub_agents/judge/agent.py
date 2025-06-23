from google.adk.agents import LlmAgent
from .prompt import JUDGE_PROMPT
from ...tools.callbacks import save_final_verdict
from ...shared_libraries import constants


judge_agent = LlmAgent(
    name="Judge",
    model=constants.MODEL,
    description="Reviews the insights from the Visionary, Architect, and Commander and provides a final verdict.",
    instruction=JUDGE_PROMPT,
    output_key="final_insight_report",
    after_agent_callback=save_final_verdict
)
