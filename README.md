# Agno Agent

A series of AI agents built using the Agno framework

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

### Prerequisites

- Python 3.12+
- uv package manager
- Anthropic API key

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   uv sync
   ```

### Configuration

Set your Anthropic API key as an environment variable:

```bash
export OPENAI_API_KEY=="your-oepnai-api-key"
```

### Usage

Run the agent:

```bash
uv run python level_1_agent.py
```

The agent will query the stock price of Apple using YFinance tools and display the results in a table format.

## Dependencies

- `agno>=1.5.10` - The Agno AI agent framework

## Project Structure

- `level_1_agent.py` - Main agent script
- `pyproject.toml` - Project configuration and dependencies
- `.python-version` - Python version specification 