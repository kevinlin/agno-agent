# Healthcare Agent MVP - Requirements Document

## Introduction

The Healthcare Agent MVP is a personal health data management system that enables a single user to upload medical report PDFs, automatically convert them to structured Markdown format, store them in a local database, and query the longitudinal health data using natural language through an AI agent interface. The system leverages OpenAI's API for document processing and the Agno framework for intelligent querying capabilities.

## Requirements

### 1. Configuration and Deployment

**User Story**: As a system administrator, I want configurable deployment options, so that I can run the healthcare agent system in my local environment with appropriate settings.

**Acceptance Criteria**:
1. The system SHALL create project structure under `agent/healthcare/` directory
2. The system SHALL provide configuration file for API keys, database paths, and model settings
3. The system SHALL support environment variable configuration for sensitive values
4. The system SHALL include dependency management file (requirements.txt or pyproject.toml)
5. The system SHALL provide setup instructions for local deployment
6. The system SHALL create necessary directories (`data/uploads/`, `data/reports/`, `data/chroma/`) on first run
7. The system SHALL create database tables automatically on first run
8. The system SHALL validate configuration on startup and report missing requirements
9. The system SHALL support configurable logging levels and output formats
10. The system SHALL log errors for debugging while protecting sensitive information
11. The system SHALL use FastAPI dependency injection with app.state for service management
12. The system SHALL implement proper service lifecycle management with startup/shutdown handlers
13. The system SHALL include unit tests for configuration validation and deployment setup
14. The system SHALL ensure all configuration and deployment tests pass before deployment
15. The system SHALL provide comprehensive README documentation with setup and usage instructions
16. The system SHALL document API endpoints and generated artifact locations in README

### 2. PDF Document Upload

**User Story**: As a patient, I want to upload my medical report PDFs to the system, so that I can digitize and organize my health records for easy access and analysis.

**Acceptance Criteria**:
1. The system SHALL implement POST /upload endpoint for PDF upload with multipart form data
2. The system SHALL accept PDF files through the REST API endpoint
3. The system SHALL validate that uploaded files are valid PDF format
4. The system SHALL compute SHA-256 hash of each uploaded PDF for deduplication
5. The system SHALL reject duplicate uploads (same hash) with appropriate error message
6. The system SHALL store the original PDF file in a structured directory (`data/uploads/`)
7. The system SHALL return a unique report identifier upon successful upload
8. The system SHALL return appropriate HTTP status codes for upload operations
9. The system SHALL provide JSON responses with consistent error formatting
10. The system SHALL include request validation and input sanitization for upload endpoint
11. The system SHALL handle file upload errors gracefully with meaningful error messages
12. The system SHALL include unit tests for PDF validation, hash computation, and error handling
13. The system SHALL ensure all upload-related tests pass before deployment

### 3. PDF Ingestion and Markdown Conversion

**User Story**: As a patient, I want my PDF medical reports automatically converted to readable Markdown format, so that the content can be easily searched and processed by AI systems.

**Acceptance Criteria**:
1. The system SHALL upload PDF files to OpenAI Files API for processing
2. The system SHALL use OpenAI Responses API with File Inputs to convert PDF to Markdown
3. The system SHALL preserve document hierarchy using ATX headings (#, ##, ###)
4. The system SHALL convert tables to Markdown table format when possible
5. The system SHALL create image placeholders for figures with descriptive captions
6. The system SHALL generate a manifest JSON describing detected tables and figures with page numbers
7. The system SHALL implement retry logic with exponential backoff for OpenAI API calls
8. The system SHALL handle conversion failures with meaningful error messages and fallback options
9. The system SHALL save the converted Markdown to local storage (`data/reports/<user_id>/<report_hash>/report.md`)
10. The system SHALL handle network timeouts and connection errors gracefully
11. The system SHALL include unit tests for OpenAI API integration, conversion logic, and error scenarios
12. The system SHALL ensure all conversion-related tests pass before deployment

### 4. Image and Asset Management

**User Story**: As a patient, I want images and figures from my medical reports to be extracted and stored locally, so that I can view them alongside the text content while maintaining privacy.

**Acceptance Criteria**:
1. The system SHALL extract embedded images from PDF files using local tools (pdfimages or pikepdf)
2. The system SHALL save extracted images to structured directories (`data/reports/<user_id>/<report_hash>/images/`)
3. The system SHALL use page-indexed naming convention for extracted images (page-003-img-01.png)
4. The system SHALL link extracted images to Markdown placeholders from the manifest
5. The system SHALL store image metadata (path, caption, alt text) in the database
6. The system SHALL handle cases where image extraction fails by preserving text captions
7. The system SHALL implement GET /api/reports/{report_id}/assets endpoint for listing assets
8. The system SHALL return appropriate HTTP status codes for asset retrieval operations
9. The system SHALL include unit tests for image extraction, file naming, and metadata storage
10. The system SHALL ensure all asset management tests pass before deployment

### 5. Data Storage, Vector Database and Embeddings

**User Story**: As a patient, I want my medical reports and metadata stored in a local database with vector embeddings, so that I can maintain control over my health data and enable semantic search capabilities.

**Acceptance Criteria**:
1. The system SHALL use SQLite database for storing metadata and relationships
2. The system SHALL implement user table with external_id field for user identification
3. The system SHALL implement medical_reports table with fields: user_id, filename, file_hash, markdown_path, images_dir, meta_json, created_at
4. The system SHALL implement report_assets table for tracking images and other assets
5. The system SHALL enforce unique constraint on (user_id, file_hash) to prevent duplicates
6. The system SHALL maintain referential integrity between users, reports, and assets
7. The system SHALL handle database connection errors and provide meaningful error messages
8. The system SHALL chunk Markdown content into semantic segments (paragraph-based initially)
9. The system SHALL generate embeddings for each chunk using OpenAI embedding model
10. The system SHALL store embeddings in Chroma vector database with metadata (user_id, report_id, chunk_index)
11. The system SHALL configure Chroma for persistent storage with proper collection naming
12. The system SHALL update vector database when new reports are ingested
13. The system SHALL implement retry logic with exponential backoff for embedding generation failures
14. The system SHALL include unit tests for database operations, vector storage, and embedding generation
15. The system SHALL ensure all data storage and embedding tests pass before deployment

### 6. Report Listing and Retrieval

**User Story**: As a patient, I want to list and view my uploaded medical reports, so that I can browse my history and access specific documents.

**Acceptance Criteria**:
1. The system SHALL implement GET /api/reports/{user_external_id} endpoint for listing reports
2. The system SHALL implement GET /api/reports/{report_id}/markdown endpoint for retrieving content
3. The system SHALL return report metadata including ID, filename, and upload date
4. The system SHALL handle cases where requested reports don't exist with appropriate HTTP status codes
5. The system SHALL ensure users can only access their own reports
6. The system SHALL provide JSON responses with consistent error formatting for retrieval endpoints
7. The system SHALL include request validation and input sanitization for retrieval endpoints
8. The system SHALL include unit tests for all retrieval endpoints and error scenarios
9. The system SHALL ensure all retrieval-related tests pass before deployment

### 7. Semantic Search and Retrieval

**User Story**: As a patient, I want to search across all my medical reports using natural language queries, so that I can quickly find relevant health information from my historical data.

**Acceptance Criteria**:
1. The system SHALL implement GET /api/{user_external_id}/search endpoint with query parameters
2. The system SHALL restrict search results to the authenticated user's data only
3. The system SHALL return search results with relevance scores and source metadata
4. The system SHALL include provenance information (report_id, chunk_index) in results
5. The system SHALL support configurable result count (k parameter)
6. The system SHALL handle empty or invalid search queries gracefully
7. The system SHALL return results in order of relevance score
8. The system SHALL return appropriate HTTP status codes for search operations
9. The system SHALL provide JSON responses with consistent error formatting for search endpoint
10. The system SHALL include request validation and input sanitization for search endpoint, including automatic whitespace stripping for all text inputs
11. The system SHALL include unit tests for search functionality, query validation, and result formatting
12. The system SHALL ensure all search-related tests pass before deployment

### 8. System Monitoring and Health Checks

**User Story**: As a system administrator, I want comprehensive health monitoring of all system services, so that I can quickly identify and resolve issues in the healthcare agent system.

**Acceptance Criteria**:
1. The system SHALL implement GET /health endpoint for comprehensive system health monitoring
2. The system SHALL expose health status for all services stored in app.state (config, database, embedding, search)
3. The system SHALL return detailed service information including model configurations and connection status
4. The system SHALL perform actual connectivity tests for database and vector database services
5. The system SHALL return appropriate HTTP status codes (200 for healthy, 503 for unhealthy/degraded)
6. The system SHALL provide structured JSON responses with service-level health details
7. The system SHALL include timestamp and version information in health responses
8. The system SHALL differentiate between "healthy", "degraded", and "unhealthy" system states
9. The system SHALL log health check failures with appropriate error details
10. The system SHALL handle health check exceptions gracefully with meaningful error responses
11. The system SHALL include unit tests for health check functionality and error scenarios
12. The system SHALL ensure all health check tests pass before deployment

### 9. AI Agent Integration

**User Story**: As a healthcare consultant, I want to interact with an AI agent that can answer questions about the patient's medical history, so that I can provide informed insights based on comprehensive data analysis.

**Acceptance Criteria**:
1. The system SHALL implement Agno agent with OpenAI chat model (gpt-5)
2. The system SHALL configure agent with SQLite storage for conversation history
3. The system SHALL integrate AgentKnowledge with Chroma vector database
4. The system SHALL implement custom medical toolkit with ingest_pdf and list_reports tools
5. The system SHALL enable agent to search and retrieve information from user's medical data
6. The system SHALL maintain conversation context and history across sessions
7. The system SHALL handle agent errors and provide meaningful responses to users
8. The system SHALL include unit tests for agent initialization, tool integration, and conversation handling
9. The system SHALL ensure all agent-related tests pass before deployment