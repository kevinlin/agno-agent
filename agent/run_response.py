from typing import Iterator

from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
from agno.utils.pprint import pprint_run_response

agent = Agent(model=OpenAIChat(id="gpt-4.1-mini"))

# Run agent and return the response as a variable
response: RunResponse = agent.run("Tell me a 50 second long story about a robot")

# Print the response in markdown format
pprint_run_response(response, markdown=True)
