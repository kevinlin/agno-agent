# Healthcare Agent MVP

A personal health data management system that enables users to upload medical report PDFs, automatically convert them to structured Markdown format, store them in a local database, and query the longitudinal health data using natural language through an AI agent interface.

## Features

- **PDF Upload & Processing**: Upload medical report PDFs with automatic conversion to structured Markdown
- **Local Data Storage**: SQLite database with vector embeddings using Chroma for semantic search
- **Image Extraction**: Extract and manage images/figures from PDF reports
- **AI-Powered Querying**: Natural language queries using Agno framework with OpenAI integration
- **REST API**: FastAPI-based web service with automatic documentation

## Prerequisites

- Python 3.12 or higher
- OpenAI API key
- Git (for cloning the repository)

## Installation & Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd agno-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root or export environment variables:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   export OPENAI_MODEL="gpt-4o-mini"  # Optional, defaults to gpt-5-mini
   export LOG_LEVEL="INFO"            # Optional, defaults to INFO
   ```

4. **Initialize the database**:
   ```bash
   python -m agent.healthcare.cli init-db
   ```

## Running the Application

### Method 1: Using the CLI (Recommended)

Start the FastAPI server using the built-in CLI:

```bash
python -m agent.healthcare.cli start
```

Options:
- `--host 0.0.0.0` - Host to bind to (default: 0.0.0.0)
- `--port 8000` - Port to bind to (default: 8000)
- `--reload` - Enable auto-reload for development
- `--log-level info` - Set log level (default: info)

Example with custom settings:
```bash
python -m agent.healthcare.cli start --host 127.0.0.1 --port 8080 --reload --log-level debug
```

### Method 2: Direct Python execution

```bash
python -m agent.healthcare.main
```

### Method 3: Using uvicorn directly

```bash
uvicorn agent.healthcare.main:app --host 0.0.0.0 --port 8000 --reload
```

## Accessing the Application

Once the server is running, you can access:

### 1. API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 2. API Endpoints

#### Health & Status
- `GET /` - Root endpoint with basic information
- `GET /health` - Health check endpoint
- `GET /config` - Application configuration (non-sensitive)

#### PDF Upload & Processing
- `POST /upload` - Upload PDF file for processing
  ```bash
  curl -X POST "http://localhost:8000/upload" \
    -F "user_external_id=john_doe" \
    -F "file=@path/to/medical_report.pdf"
  ```
  
  **Response includes**:
  - `report_id`: Unique identifier for the processed report
  - `markdown_generated`: Boolean indicating successful conversion
  - `manifest`: JSON object with detected figures and tables
  - `file_hash`: SHA-256 hash for deduplication

#### Report Management (Implementation Pending)
- `GET /reports/{user_external_id}` - List user's reports
- `GET /reports/{report_id}/markdown` - Get report content
- `GET /reports/{report_id}/assets` - List report assets

#### Search (Implementation Pending)
- `GET /reports/{user_external_id}/search?q=query` - Search reports

### 3. Generated Artifacts & Data Structure

The application creates and manages the following directory structure:

```
data/
├── uploads/           # Original PDF files
├── reports/           # Processed reports organized by user
│   └── {user_id}/
│       └── {file_hash}/
│           ├── report.md      # Converted Markdown
│           ├── manifest.json  # Tables/figures metadata
│           └── images/        # Extracted images
│               ├── page-001-img-01.png
│               └── ...
├── chroma/            # Vector database for semantic search
├── medical.db         # SQLite database (metadata)
└── agent_sessions.db  # AI agent conversation history
```

#### Accessing Generated Files

1. **Database**: SQLite files can be viewed with any SQLite browser
   - `data/medical.db` - Contains users, reports, and assets metadata
   - `data/agent_sessions.db` - AI agent conversation history

2. **Processed Reports**: 
   - Markdown files: `data/reports/{user_id}/{file_hash}/report.md`
   - Extracted images: `data/reports/{user_id}/{file_hash}/images/`
   - Metadata: `data/reports/{user_id}/{file_hash}/manifest.json`

3. **Vector Database**: Chroma database in `data/chroma/` (binary format)

## CLI Commands

The healthcare agent includes several CLI commands for management:

```bash
# Check application status
python -m agent.healthcare.cli status

# Initialize database
python -m agent.healthcare.cli init-db

# Run tests
python -m agent.healthcare.cli test

# Start server (as shown above)
python -m agent.healthcare.cli start
```

## Development & Testing

### Running Tests
```bash
# Run all tests
uv run pytest tests/ --tb=short

# Run with verbose output
uv run pytest tests/ --verbose

# Run specific test pattern
uv run pytest tests/ --tb=short --pattern "test_config*"
```

### Development Mode
For development, start the server with auto-reload:
```bash
python -m agent.healthcare.cli start --reload --log-level debug
```

### Chroma DB Administration

For development and testing purposes, you can use the Chroma DB admin interface to inspect and manage your vector database:

1. **Start the Chroma DB Admin container**:
   ```bash
   docker run --rm -p 3001:3001 fengzhichao/chromadb-admin
   ```

2. **Access the admin interface**:
   Open your browser and navigate to: http://localhost:3001/

3. **Connect to your local Chroma instance**:
   - **Chroma connection string**: `http://host.docker.internal:8100`
   - **Tenant**: `default_tenant`
   - **Database**: `default_database`
   - **Auth Type**: `No Auth`

This allows you to browse collections, inspect embeddings, and debug vector search functionality during development.

## Configuration Options

The application can be configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key |
| `OPENAI_MODEL` | `gpt-5-mini` | OpenAI chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-large` | OpenAI embedding model |
| `DATA_DIR` | `data` | Base data directory |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CHUNK_SIZE` | `1000` | Text chunking size for embeddings |
| `CHUNK_OVERLAP` | `200` | Text chunk overlap |
| `MAX_RETRIES` | `3` | Max retries for API calls |
| `REQUEST_TIMEOUT` | `30` | Request timeout in seconds |

## Troubleshooting

### Common Issues

1. **OpenAI API Key Error**:
   ```
   ValueError: OPENAI_API_KEY environment variable is required
   ```
   Solution: Set the `OPENAI_API_KEY` environment variable

2. **Database Permission Error**:
   ```
   Cannot write to data directory
   ```
   Solution: Ensure the application has write permissions to the current directory

3. **Port Already in Use**:
   ```
   OSError: [Errno 48] Address already in use
   ```
   Solution: Use a different port with `--port` option or stop the conflicting process

### Logs & Debugging

- Application logs are printed to stdout
- Increase verbosity with `--log-level debug`
- Check the `data/` directory for generated files and database content

## Architecture

The system follows a layered architecture:

- **Presentation Layer**: FastAPI REST endpoints
- **Application Layer**: Business logic services (upload, conversion, search, agent)
- **Infrastructure Layer**: Database (SQLite), vector store (Chroma), file system

For detailed architecture and design information, see:
- [Design Document](docs/specs/healthcare-agent-mvp/design.md)
- [Requirements Document](docs/specs/healthcare-agent-mvp/requirements.md)
- [Implementation Tasks](docs/specs/healthcare-agent-mvp/tasks.md)

## License

[Add your license information here]
