# Agno Agent

A series of AI agents built using the Agno framework

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

### Prerequisites

- Python 3.12+
- uv package manager
- OpenAI API key

Install uv if you don't have it:
   ```bash
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

### Usage

Run the different agent levels:

**Level 1: Agents with tools and instructions**
```bash
uv run python level_1_agent.py
```

**Level 2: Agents with knowledge and storage**
```bash
uv run python level_2_agent.py
```

**Level 3: Agents with memory and reasoning**
```bash
uv run python level_3_agent.py
```

**Level 4: Agent Teams that can reason and collaborate**
```bash
uv run python level_4_team.py
```

**Level 5: Agentic Workflows with state and determinism**
```bash
uv run python level_5_workflow.py
```

**Run Playground Server Locally**
```bash
uv run python playground.py
```

## Dependencies

- `agno>=1.5.10` - The Agno AI agent framework

## Project Structure

- `level_1_agent.py` - Main agent script
- `pyproject.toml` - Project configuration and dependencies
- `.python-version` - Python version specification 