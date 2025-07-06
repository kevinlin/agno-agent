from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.shell import ShellTools

agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    tools=[DuckDuckGoTools(), ShellTools()],
    show_tool_calls=True,
    markdown=True,
)

agent.print_response("Whats happening in France?", stream=True)

agent.print_response("Show me the contents of the current directory", markdown=True)
