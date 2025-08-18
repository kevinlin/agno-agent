# Healthcare Agent MVP - Implementation Tasks

## Overview

This document contains the implementation plan for the Healthcare Agent MVP, broken down into discrete, manageable coding tasks. Each task builds incrementally on previous steps with testable outcomes at every stage. The implementation follows test-driven development principles and ensures working functionality at each milestone.

## Implementation Tasks

### 1. Foundation and Basic Infrastructure

- [ ] 1.1 Create project structure and basic configuration
  - Create `agent/healthcare/` directory structure: `config/`, `storage/`, `__init__.py` files
  - Implement `agent/healthcare/config/config.py` with Config dataclass for basic settings
  - Add configuration loading with environment variable support
  - Create `pyproject.toml` with core dependencies: fastapi, sqlmodel, pytest
  - **Requirements**: 1.1, 1.2, 1.3, 1.4 (project structure, configuration, dependencies)
  - **Testable Outcome**: Configuration can be loaded successfully, directories are created, basic module imports work

- [ ] 1.2 Implement database models and basic storage
  - Create `agent/healthcare/storage/models.py` with User, MedicalReport, ReportAsset SQLModel classes
  - Implement `agent/healthcare/storage/database.py` with DatabaseService for table creation
  - Add database initialization and connection handling
  - Create unit tests for models and database service
  - **Requirements**: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6 (SQLite database, tables, constraints)
  - **Testable Outcome**: Database tables can be created, basic CRUD operations work, tests pass

- [ ] 1.3 Create minimal FastAPI application foundation
  - Create `agent/healthcare/main.py` with basic FastAPI app setup
  - Add health check endpoint and basic error handling
  - Implement startup/shutdown handlers for database initialization
  - Add basic logging configuration
  - **Requirements**: 1.6, 1.7, 1.9 (directory creation, database initialization, logging)
  - **Testable Outcome**: FastAPI server starts successfully, health check responds, database initializes on startup

### 2. PDF Upload and File Handling Core

- [ ] 2.1 Implement basic PDF upload service
  - Create `agent/healthcare/upload/service.py` with PDFUploadService class
  - Implement PDF validation, SHA-256 hash computation, and file storage
  - Add duplicate detection using file hash
  - Create unit tests for upload service functionality
  - **Requirements**: 2.3, 2.4, 2.5, 2.6 (PDF validation, hash computation, deduplication, storage)
  - **Testable Outcome**: Can validate PDFs, compute consistent hashes, detect duplicates, store files to disk

- [ ] 2.2 Create PDF upload REST endpoint
  - Create `agent/healthcare/upload/routes.py` with POST /ingest endpoint
  - Implement multipart form data handling and basic user management
  - Add request validation and error response formatting
  - Integrate upload service with database to store report metadata
  - **Requirements**: 2.1, 2.2, 2.7, 2.8, 2.9, 2.10 (REST endpoint, file acceptance, report ID, HTTP responses)
  - **Testable Outcome**: Can upload PDF via API, receive report_id, user and report records created in database

- [ ] 2.3 Add comprehensive upload error handling and testing
  - Implement error handling for invalid files, duplicates, and storage failures
  - Add integration tests for complete upload workflow
  - Test error scenarios and HTTP response formatting
  - **Requirements**: 2.11, 2.12, 2.13 (error handling, unit tests)
  - **Testable Outcome**: Upload endpoint handles all error cases gracefully, integration tests pass end-to-end

### 3. OpenAI Integration and PDF Conversion

- [ ] 3.1 Implement OpenAI Files API integration
  - Add OpenAI dependency and API client configuration
  - Create `agent/healthcare/conversion/service.py` with PDFConversionService
  - Implement upload_to_openai() method for Files API integration
  - Add basic retry logic and error handling for API calls
  - **Requirements**: 3.1, 3.7, 3.10 (OpenAI Files API, retry logic, timeout handling)
  - **Testable Outcome**: Can successfully upload PDF to OpenAI Files API and receive file_id

- [ ] 3.2 Implement PDF to Markdown conversion
  - Create Pydantic models for structured output: Figure, TableRef, ConversionResult
  - Implement convert_pdf_to_markdown() using Responses API with File Inputs
  - Add manifest JSON generation for tables and figures
  - Preserve document hierarchy with ATX headings and Markdown tables
  - **Requirements**: 3.2, 3.3, 3.4, 3.5, 3.6 (Responses API, document hierarchy, tables, images, manifest)
  - **Testable Outcome**: Can convert PDF to structured Markdown with manifest, hierarchy preserved

- [ ] 3.3 Add Markdown storage and conversion testing
  - Implement save_markdown() to store converted content in structured directories
  - Create comprehensive unit tests with mocked OpenAI responses
  - Add integration tests for full conversion workflow
  - Handle conversion failures with meaningful error messages
  - **Requirements**: 3.8, 3.9, 3.11, 3.12 (error handling, storage, unit tests)
  - **Testable Outcome**: Markdown files saved to correct directory structure, conversion tests pass with mock data

### 4. Vector Database and Semantic Search Foundation

- [ ] 5.1 Implement vector database integration
  - Add chromadb dependency and create `agent/healthcare/storage/embeddings.py`
  - Implement EmbeddingService with Chroma client initialization
  - Add chunk_markdown() for paragraph-based segmentation
  - Configure persistent storage with proper collection naming
  - **Requirements**: 5.8, 5.10, 5.11 (chunking, Chroma storage, collection naming)
  - **Testable Outcome**: Can initialize Chroma, chunk markdown content, store embeddings with metadata

- [ ] 5.2 Add embedding generation and storage
  - Implement generate_embeddings() using OpenAI embedding model
  - Add store_chunks() method with user and report metadata
  - Implement retry logic for embedding generation failures
  - Create unit tests for embedding service functionality
  - **Requirements**: 5.9, 5.12, 5.13, 5.14 (embedding generation, vector storage, retry logic, unit tests)
  - **Testable Outcome**: Can generate embeddings for text chunks, store in Chroma with proper metadata

- [ ] 5.3 Integrate embeddings with PDF ingestion pipeline
  - Connect embedding generation to PDF conversion workflow
  - Update ingestion endpoint to include vector database storage
  - Add comprehensive integration tests for full ingestion pipeline
  - **Requirements**: 5.12, 5.15 (vector database updates, integration tests)
  - **Testable Outcome**: Complete PDF ingestion stores embeddings, full pipeline integration tests pass

### 5. Search and Retrieval System

- [ ] 6.1 Implement semantic search service
  - Create `agent/healthcare/search/service.py` with SearchService class
  - Implement semantic_search() using Chroma vector database
  - Add user-scoped data retrieval with proper filtering
  - Create SearchResult dataclass with relevance scores and metadata
  - **Requirements**: 7.1, 7.2, 7.3, 7.4 (search endpoint, user restriction, relevance scores, provenance)
  - **Testable Outcome**: Can perform semantic search with user filtering, results include relevance scores and metadata

- [ ] 6.2 Create search API endpoint with validation
  - Create `agent/healthcare/search/routes.py` with GET /reports/{user_external_id}/search
  - Add query validation, parameter handling (k parameter)
  - Implement result ranking and JSON response formatting
  - Handle empty/invalid queries gracefully
  - **Requirements**: 7.5, 7.6, 7.7, 7.8, 7.9, 7.10 (result count, query validation, ordering, HTTP codes, JSON formatting)
  - **Testable Outcome**: Search API endpoint returns ranked results, handles all query scenarios properly

- [ ] 6.3 Add comprehensive search testing and integration
  - Create unit tests for search functionality and query validation
  - Add integration tests for complete search workflow
  - Test error scenarios and edge cases
  - **Requirements**: 7.11, 7.12 (unit tests for search functionality)
  - **Testable Outcome**: All search tests pass, integration tests validate end-to-end search functionality

### 6. Image Extraction and Asset Management

- [ ] 4.1 Implement local image extraction
  - Add pikepdf dependency and create `agent/healthcare/images/service.py`
  - Implement extract_images_pikepdf() for local image extraction
  - Add page-indexed naming convention (page-003-img-01.png)
  - Create AssetMetadata dataclass and basic linking to manifest
  - **Requirements**: 4.1, 4.2, 4.3, 4.4 (image extraction, storage directories, naming, manifest linking)
  - **Testable Outcome**: Can extract images from PDF, save with correct naming, link to manifest placeholders

- [ ] 4.2 Integrate image extraction with conversion workflow
  - Connect image extraction to PDF conversion process
  - Store image metadata in database via ReportAsset records
  - Handle cases where image extraction fails gracefully
  - Add unit tests for image extraction and metadata storage
  - **Requirements**: 4.5, 4.6, 4.9 (metadata storage, extraction failure handling, unit tests)
  - **Testable Outcome**: Complete PDF ingestion with images extracted and stored, database records created

- [ ] 4.3 Create asset retrieval API endpoint
  - Create `agent/healthcare/images/routes.py` with GET /reports/{report_id}/assets
  - Implement asset listing with proper user access control
  - Add HTTP status codes and JSON response formatting
  - Create integration tests for asset retrieval
  - **Requirements**: 4.7, 4.8, 4.10 (asset endpoint, HTTP status codes, unit tests)
  - **Testable Outcome**: Can retrieve asset lists via API, access control enforced, integration tests pass

### 7. Report Management and Content Retrieval

- [ ] 7.1 Implement report service layer
  - Create `agent/healthcare/reports/service.py` with ReportService class
  - Implement list_user_reports() and get_report_markdown() methods
  - Add validate_user_access() for access control
  - Create unit tests for report service functionality
  - **Requirements**: 6.3, 6.5, 6.8 (report metadata, user access control, unit tests)
  - **Testable Outcome**: Can list user reports, retrieve markdown content, access control enforced

- [ ] 7.2 Create report management API endpoints
  - Create `agent/healthcare/reports/routes.py` with report listing and retrieval endpoints
  - Implement GET /reports/{user_external_id} and GET /reports/{report_id}/markdown
  - Add request validation, error handling, and JSON response formatting
  - **Requirements**: 6.1, 6.2, 6.4, 6.6, 6.7 (listing endpoint, markdown retrieval, error handling, JSON formatting, validation)
  - **Testable Outcome**: Report management APIs work correctly, proper error handling for missing reports

- [ ] 7.3 Add report management testing and integration
  - Create comprehensive unit tests for all retrieval endpoints
  - Add integration tests for report management workflow
  - Test user access control and error scenarios
  - **Requirements**: 6.9 (unit tests for retrieval functionality)
  - **Testable Outcome**: All report management tests pass, integration tests validate complete functionality

### 8. AI Agent Integration with Medical Toolkit

- [ ] 8.1 Implement Agno agent medical toolkit
  - Add agno dependency and create `agent/healthcare/agent/toolkit.py`
  - Implement MedicalToolkit with ingest_pdf, list_reports, search_medical_data tools
  - Add proper error handling and response formatting for tools
  - Create unit tests for toolkit functionality
  - **Requirements**: 8.4, 8.5, 8.8 (medical toolkit, search capabilities, unit tests)
  - **Testable Outcome**: Medical toolkit tools work correctly, can interact with existing services

- [ ] 8.2 Create healthcare agent configuration and service
  - Create `agent/healthcare/agent/service.py` with HealthcareAgent class
  - Implement create_healthcare_agent() with proper Agno configuration
  - Configure OpenAI chat model (gpt-5) and AgentKnowledge with Chroma
  - Add agent session management with SQLite storage
  - **Requirements**: 8.1, 8.2, 8.3, 8.6 (Agno agent, SQLite storage, Chroma integration, conversation history)
  - **Testable Outcome**: Agent initializes correctly, can access knowledge base, maintains conversation history

- [ ] 8.3 Integrate agent with application and add testing
  - Add agent endpoints to main FastAPI application
  - Implement agent error handling with meaningful responses
  - Create comprehensive unit tests for agent integration
  - Add integration tests for agent workflow with medical toolkit
  - **Requirements**: 8.7, 8.9 (agent error handling, unit tests)
  - **Testable Outcome**: Agent integrated with application, can answer questions using medical data, all tests pass

### 9. Application Integration and End-to-End Workflow

- [ ] 9.1 Complete FastAPI application assembly
  - Integrate all router modules (upload, search, reports, images, agent)
  - Add comprehensive error handling and middleware
  - Implement dependency injection for all services
  - Create application CLI for server management
  - **Testable Outcome**: Complete application starts successfully, all endpoints accessible, proper dependency injection

- [ ] 9.2 Create comprehensive integration test suite
  - Create `tests/agent/healthcare/test_integration_full_workflow.py`
  - Test complete PDF upload → conversion → storage → search → agent query workflow
  - Create `tests/agent/healthcare/test_integration_api_endpoints.py` for all API endpoints
  - Add database operations integration tests
  - **Testable Outcome**: Full end-to-end workflow tests pass, all API integration tests validate complete functionality

- [ ] 9.3 Add test fixtures and production readiness
  - Create comprehensive test fixtures in `tests/agent/healthcare/fixtures/`
  - Add sample medical reports and mock responses
  - Implement proper logging and monitoring throughout application
  - Add configuration validation and startup checks
  - **Testable Outcome**: All tests run reliably with fixtures, application production-ready with proper logging and validation

## Testing and Quality Assurance

Each implementation task includes specific testable outcomes that validate functionality before proceeding to the next task. The approach ensures:

- **Incremental Building**: Each task builds working functionality on previous tasks
- **Testable Milestones**: Clear, measurable outcomes at every stage
- **Integration Focus**: Regular integration testing prevents big-bang integration issues
- **Quality Gates**: No task completion without passing tests

## Implementation Flow

The tasks are structured to enable:

1. **Foundation First**: Basic infrastructure and configuration
2. **Core Services**: PDF processing and storage built incrementally
3. **API Layer**: REST endpoints added as services are completed
4. **Advanced Features**: Search and AI capabilities built on stable foundation
5. **Integration**: Comprehensive testing and production readiness

Each task can be completed independently while building toward the complete system, with working functionality demonstrable at every stage.