# Agno Agent

A series of AI agents built using the Agno framework

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

### Prerequisites

- Python 3.12+
- uv package manager
- OpenAI API key

### Install `uv`

We use `uv` for python environment and package management. Install it by following the the [`uv` documentation](https://docs.astral.sh/uv/#getting-started) or use the command below for unix-like systems:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

1. Clone the repository

2. Setup your virtual environment:
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

### Configuration

Set your OpenAI API key as an environment variable:

```bash
export OPENAI_API_KEY=="your-oepnai-api-key"
```

### Code Formatting

This project uses `black` for code formatting and `isort` for import sorting, both configured in `pyproject.toml`.

**Format code and sort imports (recommended):**
```bash
uv run black . && uv run isort .
```

**Check formatting and import sorting without making changes:**
```bash
uv run black --check . && uv run isort --check-only .
```

**Show formatting and import sorting diff without making changes:**
```bash
uv run black --diff . && uv run isort --diff .
```

### Usage

Run the different agent levels:

**Level 1: Agents with tools and instructions**
```bash
uv run python agent/level_1_agent.py
```

**Level 2: Agents with knowledge and storage**
```bash
uv run python agent/level_2_agent.py
```

**Level 3: Agents with memory and reasoning**
```bash
uv run python agent/level_3_agent.py
```

**Level 4: Agent Teams that can reason and collaborate**
```bash
uv run python agent/level_4_team.py
```

**Level 5: Agentic Workflows with state and determinism**
```bash
uv run python agent/level_5_workflow.py
```

**Run Research Agent**
```bash
uv run python agent/research_agent.py
```

**Run Playground Server Locally**
```bash
uv run python playground/playground.py
```

## Dependencies

- `agno>=1.7.0` - The Agno AI agent framework
- `black>=24.0.0` - Python code formatter
- `isort>=5.13.2` - Python import sorting tool

## Project Structure

- `agent/` - Contains all agent implementations
- `playground/` - Contains playground server
- `pyproject.toml` - Project configuration and dependencies
- `.python-version` - Python version specification 