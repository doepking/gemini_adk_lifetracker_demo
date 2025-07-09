from google.adk.agents import BaseAgent, LlmAgent, FinalResponse
from google.adk.tools.tool_protos import ToolCall
from google.adk.agents.agent_protos import AgentContext, AgentEvent
from typing import AsyncGenerator

class CustomAgent(BaseAgent):
    async def _run_async_impl(
        self,
        context: AgentContext,
    ) -> AsyncGenerator[AgentEvent, None]:
        # Step 1: Use an LlmAgent to select a tool or generate a response.
        # We pass through any callbacks from this agent to the inner agent.
        llm_agent = LlmAgent(
            model=self.model,
            instruction=self.instruction,
            tools=self.tools,
            name=f"{self.name}_LlmAgent",
            before_agent_callback=self.before_agent_callback,
            after_tool_callback=self.after_tool_callback,
            before_model_callback=self.before_model_callback,
            after_model_callback=self.after_model_callback,
        )

        # Step 2: Intercept the events from the LlmAgent.
        async for event in llm_agent.run_async(context):
            if event.type == "TOOL_CALL":
                # A tool was called, so we take over the execution flow.
                # First, yield the TOOL_CALL event itself so the caller sees it.
                yield event

                # Execute the tool.
                tool_execution_result = await self._execute_tool(event.tool_call, context)
                yield tool_execution_result

                # Create and yield our own final response, skipping the summarization.
                yield FinalResponse(output=tool_execution_result.tool_result.output)

                # We are done, so we exit the generator.
                return
            else:
                # For any other event type (e.g., MODEL_START, or a FINAL_RESPONSE for chat),
                # just pass it through. If the event is a FINAL_RESPONSE, the generator
                # will correctly terminate execution.
                yield event
