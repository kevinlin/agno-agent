from typing import List

from agno.agent import Agent, RunResponse
from agno.models.openai import OpenAIChat
from pydantic import BaseModel, Field
from rich.pretty import pprint


class MovieScript(BaseModel):
    setting: str = Field(
        ..., description="Provide a nice setting for a blockbuster movie."
    )
    ending: str = Field(
        ...,
        description="Ending of the movie. If not available, provide a happy ending.",
    )
    genre: str = Field(
        ...,
        description="Genre of the movie. If not available, select action, thriller or romantic comedy.",
    )
    name: str = Field(..., description="Give a name to this movie")
    characters: List[str] = Field(..., description="Name of characters for this movie.")
    storyline: str = Field(
        ..., description="3 sentence storyline for the movie. Make it exciting!"
    )


# Agent that uses JSON mode
json_mode_agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    description="You write movie scripts.",
    response_model=MovieScript,
    use_json_mode=True,
)
json_mode_agent.print_response("New York", stream=True, stream_intermediate_steps=True)

# Agent that uses structured outputs
structured_output_agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    description="You write movie scripts.",
    response_model=MovieScript,
)
structured_output_agent.print_response(
    "New York", stream=True, stream_intermediate_steps=True
)

# Agent that uses a parser model
parser_model_agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    description="You write movie scripts.",
    response_model=MovieScript,
    parser_model=OpenAIChat(id="gpt-4o"),
)
parser_model_agent.print_response(
    "New York", stream=True, stream_intermediate_steps=True
)
