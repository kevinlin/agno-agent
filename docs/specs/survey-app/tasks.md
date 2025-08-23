# Survey App - Implementation Tasks

This document outlines the implementation tasks for the Survey App feature, organized incrementally where each task builds upon previous ones and can be tested or verified manually.

## Architecture Changes

**Simplified Response Storage:**
- **Previous**: Individual answers stored in separate `survey_answers` table
- **Current**: Complete survey state stored in `user_response` JSON field on `survey_responses` table
- **Benefits**: Simplified schema, easier state management, atomic saves, better performance

**Unified API Endpoint:**  
- **Previous**: Separate endpoints for individual answers (`POST /api/survey-response/answer`) and completion
- **Current**: Single `POST /api/survey-response` endpoint handles both partial and complete saves
- **Benefits**: Simpler API, consistent state handling, reduced complexity

**Enhanced Frontend State Management:**
- Frontend maintains complete answer state and saves entire response object
- State reconstruction from `user_response` JSON for resume functionality  
- Simplified auto-save logic with complete state persistence

## Implementation Tasks

- [x] **1. Database Foundation Setup**
  - Create `Survey`, `SurveyResponse`, `SurveyResult` SQLModel classes in `healthcare/storage/models.py`
  - Add `user_response` JSON field to `SurveyResponse` model for storing answer data
  - Remove `SurveyAnswer` model in favor of simplified user_response JSON storage
  - Update `healthcare/storage/database.py` to create survey tables with proper indexes
  - Add survey table creation to existing `create_tables()` method
  - Create unit tests for all database models and relationships
  - **Testable**: Database tables created successfully, can insert/query records with JSON data, all model tests pass
  - **Requirements**: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7

- [x] **2. Survey Service and Data Management**
  - Create `healthcare/survey/service.py` with `SurveyService` class following healthcare patterns
  - Implement survey CRUD operations (create, get by code, list surveys)
  - Add survey JSON validation and schema storage with personalization survey compatibility
  - Create script to load personalization-survey.json into database
  - Write comprehensive unit tests for survey service methods
  - **Testable**: Can create, retrieve, and validate surveys; personalization survey loads successfully
  - **Requirements**: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7

- [x] **3. Survey Response Management**
  - Add survey response management methods to `SurveyService`
  - Implement response lookup by user_id and survey_code with user_response JSON field
  - Add response creation, complete state saving, and progress tracking
  - Implement survey completion with derived metrics calculation from user_response JSON
  - Create unit tests for response management functionality
  - **Testable**: Can create, update responses; save complete answer state; calculate progress and completion
  - **Requirements**: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 6.7

- [x] **4. Survey API Endpoints**
  - Create `healthcare/survey/routes.py` with FastAPI router and proper error handling
  - Implement survey catalog endpoints: `GET /api/survey`, `GET /api/survey/{code}`, `POST /api/survey`
  - Add unified survey response endpoint: `GET /api/survey-response`, `POST /api/survey-response` (handles both partial and complete saves)
  - Remove separate answer endpoint in favor of unified response handling
  - Implement `POST /api/survey-links` for agent integration
  - Integrate survey routes with main application in `healthcare/main.py`
  - Create comprehensive API endpoint tests
  - **Testable**: All survey endpoints work correctly, unified response handling, proper error handling, agent integration functional
  - **Requirements**: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9

- [x] **5. Frontend API Integration**
  - Create survey API client functions in `healthcare/app/lib/survey-api.ts` with TypeScript types
  - Update `healthcare/app/hooks/use-survey.ts` to integrate with unified response API
  - Enhance `healthcare/app/hooks/use-survey-persistence.ts` with complete state synchronization
  - Add proper error handling, retry logic, and optimistic updates for complete state saves
  - Implement state reconstruction from user_response JSON data
  - Create tests for API client functions and enhanced hooks
  - **Testable**: Frontend can load surveys from backend, save complete state automatically, reconstruct from partial states, proper error recovery
  - **Requirements**: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 3.3, 3.4, 3.5, 3.10, 7.4, 7.5, 7.9

- [x] **6. Branching Logic Implementation**
  - Create branching logic evaluation functions in `healthcare/app/lib/branching.ts`
  - Support all condition operators (equals, one_of, includes, gt/gte/lt/lte, and/or/not)
  - Implement question visibility calculation and answer voiding
  - Integrate branching logic with survey state management hooks
  - Add comprehensive tests for branching rule evaluation and question filtering
  - **Testable**: Branching rules evaluate correctly, questions show/hide based on answers, navigation respects rules
  - **Requirements**: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.5

- [x] **7. Survey Component Enhancement**
  - Update `healthcare/app/components/survey/survey-container.tsx` with backend integration
  - Add loading states, error boundaries, and survey response loading
  - Create survey completion components with results display and derived metrics
  - Add comprehensive error handling with user-friendly messages and recovery options
  - Implement loading skeletons and progress indicators
  - Create component tests for all enhanced survey components
  - **Testable**: Survey container loads from backend, completion flow works, proper error/loading states
  - **Requirements**: 9.1, 9.2, 9.5, 9.6, 9.8, 6.3, 6.4, 6.5, 6.6, 6.7, 3.1, 3.2

- [x] **8. Survey Page Integration**
  - Update `healthcare/app/app/survey/[surveyCode]/page.tsx` with backend integration
  - Add proper user_id parameter handling from URL
  - Implement survey loading, error handling for not found cases, and resume functionality
  - Add proper TypeScript types and error boundaries
  - Create page-level tests for survey routing and parameter handling
  - **Testable**: Survey page loads correctly with user_id parameter, proper error handling, resume works
  - **Requirements**: 5.1, 5.2, 5.3, 5.6, 5.7, 3.5

- [x] **8.1. Home Page API Integration**
  - Update `healthcare/app/app/page.tsx` to use backend API instead of hardcoded data
  - Replace `getAllSurveys()` with calls to `GET /api/survey` and `GET /api/survey/{code}`
  - Create server-side API client functions (`lib/survey-api-server.ts`) for SSR compatibility
  - Implement proper error handling and fallback states for API failures
  - Add loading states and user-friendly error messages
  - Ensure all tests pass after integration changes
  - **Testable**: Home page loads surveys from backend API, displays proper error states, all tests pass
  - **Requirements**: 9.9, 9.10, 7.1, 7.2

- [ ] **9. Question Type Support and Validation**
  - Enhance existing question renderer components in `healthcare/app/components/survey/`
  - Add proper validation feedback, error states, and accessibility compliance
  - Ensure support for all question types: INPUT, SINGLE_SELECT, MULTIPLE_SELECT, DROPDOWN, TIME
  - Implement exclusive options handling and proper unit text display
  - Add keyboard navigation and screen reader support
  - Create comprehensive component tests for all question types
  - **Testable**: All question types render correctly, validation works, accessibility compliant
  - **Requirements**: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 9.3, 9.4, 9.7

- [ ] **10. Progress Tracking and Navigation**
  - Implement progress percentage calculation based on visible questions
  - Add progress bar and navigation controls (Next/Back buttons)
  - Implement single-question navigation with proper validation
  - Add review screen functionality with answer editing capability
  - Support direct navigation to specific questions via URL
  - Create tests for navigation logic and progress calculation
  - **Testable**: Progress tracking accurate, navigation works correctly, review screen functional
  - **Requirements**: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6

- [ ] **11. Integration Testing and Workflow Verification**
  - Create integration tests for complete survey workflows
  - Test end-to-end user journey from survey start to completion
  - Verify branching logic works with real survey data
  - Test resume functionality and progress persistence
  - Add healthcare agent integration testing
  - **Testable**: Complete personalization survey works end-to-end, all user scenarios covered
  - **Requirements**: All requirements integrated and working together

## Task Dependencies

- **Tasks 1-2**: Database and service foundation
- **Tasks 3-4**: Backend API implementation (depends on 1-2)
- **Tasks 5-6**: Frontend integration and logic (depends on 4)
- **Tasks 7-10**: UI components and user experience (depends on 5-6)
- **Task 11**: Final integration and testing (depends on all previous)

## Verification Methods

Each task can be verified through:
- **Unit tests**: Automated tests for individual components
- **Manual testing**: Direct testing of functionality through UI or API
- **Integration testing**: Testing component interactions
- **End-to-end testing**: Complete user workflow verification