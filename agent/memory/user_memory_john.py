from agno.agent import Agent
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.memory.v2.memory import Memory
from agno.models.openai import OpenAIChat

memory_db = SqliteMemoryDb(table_name="memory", db_file="tmp/memory.db")
memory = Memory(db=memory_db)

john_doe_id = "john_doe@example.com"

agent = Agent(
    model=OpenAIChat(id="gpt-4.1-mini"),
    memory=memory,
    enable_agentic_memory=True,
)

# The agent can add new memories to the user's memory
agent.print_response(
    "My name is John Doe and I like to hike in the mountains on weekends.",
    stream=True,
    user_id=john_doe_id,
)

agent.print_response("What are my hobbies?", stream=True, user_id=john_doe_id)

# The agent can also remove all memories from the user's memory
agent.print_response(
    "Remove all existing memories of me. Completely clear the DB.",
    stream=True,
    user_id=john_doe_id,
)

agent.print_response(
    "My name is John Doe and I like to paint.", stream=True, user_id=john_doe_id
)

# The agent can remove specific memories from the user's memory
agent.print_response("Remove any memory of my name.", stream=True, user_id=john_doe_id)
