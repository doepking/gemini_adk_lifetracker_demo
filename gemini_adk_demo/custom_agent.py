from typing import Any, AsyncGenerator, Callable, List

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions


class CustomAgent(BaseAgent):
    """A custom agent that bypasses the second LLM call for tool summarization."""

    # --- Field Declarations for Pydantic ---
    # These fields are expected by the LlmAgent that we create internally.
    model: str
    instruction: str
    tools: List[Any]
    output_key: str | None = None
    before_agent_callback: Callable | None = None
    after_tool_callback: Callable | None = None
    before_model_callback: Callable | None = None
    after_model_callback: Callable | None = None

    model_config = {"arbitrary_types_allowed": True}

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncGenerator[Event, None]:
        """Orchestrates the agent flow, skipping summarization for tool calls."""
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
        async for event in llm_agent.run_async(ctx):
            # Check if the event contains the result of a tool execution.
            if event.get_function_responses():
                # A tool was successfully executed by the LlmAgent.
                # Now, we modify the result event to prevent the summarization step.
                if event.actions:
                    event.actions.skip_summarization = True
                else:
                    event.actions = EventActions(skip_summarization=True)

                # Yield the modified event. The framework will see the flag
                # and treat this as a final response, ending the turn.
                yield event

                # We are done with this turn, so we exit the generator,
                # preventing the LlmAgent from proceeding to summarize.
                return
            else:
                # For any other event type (e.g., TOOL_CALL, MODEL_START, or a final text response),
                # just pass it through. If it's a final response for chat,
                # the generator will correctly terminate execution.
                yield event
