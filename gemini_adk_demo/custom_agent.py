from google.adk.agents import BaseAgent, LlmAgent, FinalResponse
from google.adk.tools.tool_protos import ToolCall
from google.adk.agents.agent_protos import AgentContext, AgentEvent
from typing import AsyncGenerator

class CustomAgent(BaseAgent):
    async def _run_async_impl(
        self,
        context: AgentContext,
    ) -> AsyncGenerator[AgentEvent, None]:
        # Step 1: Use an LlmAgent to select a tool
        llm_agent = LlmAgent(
            model=self.model,
            instruction=self.instruction,
            tools=self.tools,
            name=f"{self.name}_LlmAgent",
        )

        tool_selection_events = [
            event async for event in llm_agent.run_async(context)
        ]

        # Find the tool call in the events
        tool_call = None
        for event in tool_selection_events:
            yield event
            if event.type == "TOOL_CALL":
                tool_call = event.tool_call
                break

        if not tool_call:
            yield FinalResponse(
                output={"status": "error", "message": "No tool was selected."}
            )
            return

        # Step 2: Execute the tool
        tool_execution_result = await self._execute_tool(tool_call, context)
        yield tool_execution_result

        # Step 3: Return the tool's output directly
        yield FinalResponse(output=tool_execution_result.tool_result.output)
