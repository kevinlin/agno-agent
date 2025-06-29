import json
from typing import Iterator

from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from agno.tools.yfinance import YFinanceTools
from agno.utils.pprint import pprint_run_response

agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    tools=[
        ReasoningTools(add_instructions=True),
        YFinanceTools(stock_price=True),
    ],
    markdown=True,
    show_tool_calls=True,
)

response_stream: Iterator[RunResponse] = agent.run(
    "What is the most valuable company in the world right now?",
    stream=True,
    stream_intermediate_steps=True,
)

# Print event per message
for event in response_stream:
    if event.event == "RunStarted":
        print(f"{event.event}->")
        print(json.dumps(event.__dict__, indent=2, default=str))
    elif event.event == "RunCompleted":
        print(
            f"{event.event}->\nResponse: {event.content}\nReasoning: {event.reasoning_content or ''}"
        )
    elif event.event == "RunResponseContent":
        print(f"Content: {event.content}")
    elif event.event == "ToolCallStarted":
        print(
            f"{event.event}->\ttool_name: {event.tool.tool_name}, tool_args: {event.tool.tool_args}"
        )
    elif event.event == "ToolCallCompleted":
        tool_call_result = getattr(
            event.tool,
            "result",
            getattr(event.tool, "tool_call_error", "No tool call error"),
        )
        print(f"{event.event}->\n{tool_call_result}")
    elif (
        event.event == "ReasoningStarted"
        or event.event == "ReasoningStep"
        or event.event == "ReasoningCompleted"
    ):
        reasoning_content = getattr(
            event,
            "reasoning_content",
            getattr(event, "reasoning_steps", "No reasoning content"),
        )
        print(f"{event.event}: {reasoning_content}")
    else:
        print(f"{event.event}->\t")
        print(json.dumps(event.__dict__, indent=2, default=str))


# Print the response stream in markdown format
pprint_run_response(response_stream, markdown=True)
