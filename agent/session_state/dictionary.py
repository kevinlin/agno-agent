from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat


# Define tools to manage our dictionary
def add_translation(agent: Agent, german_word: str, english_word: str) -> str:
    """Add a German-English translation pair to the dictionary and return confirmation."""
    # Add the translation if it's not already in the dictionary
    dictionary = agent.session_state["dictionary"]
    german_lower = german_word.lower()

    if german_lower in dictionary:
        return f"'{german_word}' is already in the dictionary with translation '{dictionary[german_lower]}'"

    dictionary[german_lower] = english_word
    return f"Added translation: '{german_word}' -> '{english_word}'"


def remove_translation(agent: Agent, german_word: str) -> str:
    """Remove a translation from the dictionary by German word."""
    # Case-insensitive search
    german_lower = german_word.lower()
    dictionary = agent.session_state["dictionary"]

    if german_lower in dictionary:
        english_translation = dictionary.pop(german_lower)
        return f"Removed translation: '{german_word}' -> '{english_translation}'"

    return f"'{german_word}' was not found in the dictionary"


def translate_word(agent: Agent, german_word: str) -> str:
    """Translate a German word to English using the dictionary."""
    german_lower = german_word.lower()
    dictionary = agent.session_state["dictionary"]

    if german_lower in dictionary:
        return f"'{german_word}' translates to '{dictionary[german_lower]}'"

    return f"'{german_word}' not found in dictionary. Please add it first."


def list_translations(agent: Agent) -> str:
    """List all translations in the dictionary."""
    dictionary = agent.session_state["dictionary"]

    if not dictionary:
        return "The dictionary is empty."

    translations_text = "\n".join(
        [f"- {german.title()} -> {english}" for german, english in dictionary.items()]
    )
    return f"Current dictionary:\n{translations_text}"


def search_by_english(agent: Agent, english_word: str) -> str:
    """Find German word(s) that translate to the given English word."""
    english_lower = english_word.lower()
    dictionary = agent.session_state["dictionary"]

    matches = [
        german
        for german, english in dictionary.items()
        if english.lower() == english_lower
    ]

    if not matches:
        return f"No German words found that translate to '{english_word}'"

    if len(matches) == 1:
        return f"'{matches[0].title()}' translates to '{english_word}'"
    else:
        german_words = ", ".join([word.title() for word in matches])
        return f"German words that translate to '{english_word}': {german_words}"


# Create a Dictionary Agent that maintains state
agent = Agent(
    model=OpenAIChat(id="gpt-5-mini"),
    # Initialize the session state with an empty dictionary
    session_state={"dictionary": {}},
    tools=[
        add_translation,
        remove_translation,
        translate_word,
        list_translations,
        search_by_english,
    ],
    # You can use variables from the session state in the instructions
    instructions=dedent(
        """\
        Your job is to manage a German-English dictionary.

        The dictionary starts empty. You can:
        - Add German-English translation pairs
        - Remove translations by German word
        - Translate German words to English
        - List all translations
        - Search for German words by English translation

        Current dictionary: {dictionary}
    """
    ),
    show_tool_calls=True,
    add_state_in_messages=True,
    markdown=True,
)

# Example usage
agent.print_response(
    "Add some basic German words: Hund means dog, Katze means cat, and Haus means house",
    stream=True,
)
print(f"Session state: {agent.session_state}")

agent.print_response("What does Hund mean?", stream=True)
print(f"Session state: {agent.session_state}")

agent.print_response("Add more words: Buch means book, Auto means car", stream=True)
print(f"Session state: {agent.session_state}")

agent.print_response("What German words do I have in my dictionary?", stream=True)
print(f"Session state: {agent.session_state}")

agent.print_response("What German word means 'cat'?", stream=True)
print(f"Session state: {agent.session_state}")

agent.print_response("Remove Haus from the dictionary", stream=True)
print(f"Session state: {agent.session_state}")

agent.print_response("Show me my current dictionary", stream=True)
print(f"Session state: {agent.session_state}")
