# Survey App - Requirements Document

## Introduction

The Survey App is a comprehensive web-based survey application designed to integrate with the existing healthcare agent system. The application consists of a FastAPI backend with SQLite database and a Next.js frontend that renders surveys one question at a time, supports conditional branching, and provides seamless user experience with progress tracking and resume capabilities.

The system is designed to work with flat question arrays (removing the sections requirement from the original functional specification) and must be compatible with existing survey data structures like the personalization-survey.json.

## Requirements

### 1. Survey Data Management

**User Story**: As a system administrator, I want to manage survey definitions and versions, so that I can deploy and maintain different surveys for users.

**Acceptance Criteria**:
1. The system SHALL store survey definitions with unique codes, titles, versions, and types
2. The system SHALL support survey types: PERSONALIZATION, DISEASE_RISK, LIFE_STYLE
3. The system SHALL support immutable survey versions (new versions create new records)
4. The system SHALL provide API endpoints to create, retrieve, and list surveys (Service layer ready)
5. The system SHALL validate survey JSON structure before storage
6. The system SHALL support flat question arrays without requiring sections

**Implementation Notes**:
- SurveyService class provides complete CRUD operations
- Comprehensive validation for survey definitions, questions, and branching rules
- Support for all question types: INPUT, SINGLE_SELECT, MULTIPLE_SELECT, DROPDOWN, TIME
- Personalization survey successfully loaded and validated
- Proper error handling with HTTP status codes

### 2. Question Type Support

**User Story**: As a survey respondent, I want to answer different types of questions, so that I can provide comprehensive health information.

**Acceptance Criteria**:
1. The system SHALL support INPUT questions with INTEGER_NUMBER and DECIMAL_NUMBER units
2. The system SHALL support SINGLE_SELECT questions with radio button selection
3. The system SHALL support MULTIPLE_SELECT questions with checkbox selection
4. The system SHALL support DROPDOWN questions with select menu
5. The system SHALL support TIME questions with minute-based input
6. The system SHALL validate input constraints (min/max values, required fields)
7. The system SHALL support exclusive options in MULTIPLE_SELECT questions
8. The system SHALL display unit text alongside input controls

### 3. Survey Response Management

**User Story**: As a survey respondent, I want my progress to be saved automatically, so that I can resume the survey later without losing my answers.

**Acceptance Criteria**:
1. The system SHALL look up existing survey responses by user_id and survey_code
2. The system SHALL track response status: in_progress, completed, cancelled
3. The system SHALL save answers automatically after each valid input
4. The system SHALL calculate and update progress percentage
5. The system SHALL provide resume capability via URLs
6. The system SHALL allow users to review saved results before final submission
7. The system SHALL overwrite existing in_progress responses for the same user-survey

### 4. Conditional Branching Logic

**User Story**: As a survey designer, I want to implement conditional question flow, so that users only see relevant questions based on their previous answers.

**Acceptance Criteria**:
1. The system SHALL evaluate branching rules in real-time on the frontend
2. The system SHALL support rule operators: equals, one_of, includes, gt/gte/lt/lte, and/or/not
3. The system SHALL support branching actions: skip_questions, goto_question, insert_questions_after, require_questions
4. The system SHALL void answers for questions that become hidden due to branching
5. The system SHALL recalculate question visibility after each answer change
6. The system SHALL handle backtracking when previous answers change
7. The system SHALL support question-level visible_if conditions

### 5. Single-Question Navigation

**User Story**: As a survey respondent, I want to answer one question at a time, so that I can focus on each question without being overwhelmed.

**Acceptance Criteria**:
1. The system SHALL display only one question per screen
2. The system SHALL provide Next/Back navigation buttons
3. The system SHALL disable Next button until valid answer is provided for required questions
4. The system SHALL show field-level validation error messages
5. The system SHALL calculate next question based on branching logic
6. The system SHALL support direct navigation to specific questions via URL
7. The system SHALL handle navigation for conditional questions appropriately

### 6. Progress Tracking and Review

**User Story**: As a survey respondent, I want to see my progress and review my answers, so that I can understand how much is left and verify my responses.

**Acceptance Criteria**:
1. The system SHALL display progress percentage based on answered questions
2. The system SHALL show progress bar or indicator on each screen
3. The system SHALL provide a review screen before final submission
4. The system SHALL allow editing individual answers from the review screen
5. The system SHALL group answers logically for review (by question index/type)
6. The system SHALL show question titles and selected answers in review
7. The system SHALL calculate derived metrics (e.g., BMI) on completion

### 7. API Integration

**User Story**: As a healthcare agent, I want to generate survey links and check completion status, so that I can guide users through the survey process.

**Acceptance Criteria**:
1. The system SHALL provide API to generate signed survey URLs with user_id and survey_code
2. The system SHALL provide API to check survey completion status
3. The system SHALL provide API to retrieve survey responses and answers
4. The system SHALL provide API to submit completed surveys
5. The system SHALL return structured response data with ok/error format
6. The system SHALL support external user ID mapping to internal user records
7. The system SHALL provide APIs for answer persistence during survey taking

### 8. Database Schema Implementation

**User Story**: As a system administrator, I want a robust database schema, so that survey data is stored reliably and efficiently.

**Acceptance Criteria**:
1. The system SHALL implement surveys table with id, code, title, version, type, description, created_at
2. The system SHALL implement survey_responses table with response tracking by user_id and survey_code
3. The system SHALL implement survey_answers table with answer storage linked to responses
4. The system SHALL implement survey_results table for computed assessment outputs
5. The system SHALL create appropriate indexes for performance optimization
6. The system SHALL reuse existing users table from the healthcare system
7. The system SHALL support JSON storage for flexible answer values

**Implementation Notes**:
- Database models defined in `healthcare/storage/models.py`
- Survey definitions stored as JSON in `definition_json` column
- UUID-based primary keys for surveys and survey responses
- Proper foreign key relationships and constraints
- Unique constraints for survey codes and user-survey response pairs

### 9. Frontend User Experience

**User Story**: As a survey respondent, I want an intuitive and modern interface, so that I can complete surveys efficiently and enjoyably.

**Acceptance Criteria**:
1. The system SHALL provide a responsive design that works on mobile and desktop
2. The system SHALL use modern UI components with consistent styling
3. The system SHALL show clear question titles, subtitles, and help text
4. The system SHALL provide appropriate input controls for each question type
5. The system SHALL show loading states during navigation and saving
6. The system SHALL provide clear error messages and validation feedback
7. The system SHALL support keyboard navigation and accessibility standards
8. The system SHALL show survey completion confirmation with results summary

### 10. Data Compatibility and Migration

**User Story**: As a system integrator, I want the system to work with existing survey data, so that current surveys can be migrated without modification.

**Acceptance Criteria**:
1. The system SHALL be compatible with personalization-survey.json structure
2. The system SHALL handle surveys without sections (flat question arrays)
3. The system SHALL support existing question codes and answer codes
4. The system SHALL maintain backward compatibility with existing answer formats
5. The system SHALL provide migration path from sectioned to flat question structure
6. The system SHALL validate existing survey data against the schema
7. The system SHALL support empty branching_rules arrays for simple surveys

**Implementation Notes**:
- Personalization survey (9 questions) successfully loaded from JSON file
- Survey loader script available at `scripts/load_personalization_survey.py`
- Validation system handles all existing survey formats
- Proper support for all question types used in personalization survey
- Branching rules validation allows empty arrays
