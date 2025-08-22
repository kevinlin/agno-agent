# Survey App — Functional Requirements

*Last updated: 22-Aug-2025*

## 0. Objective

Deliver a **separately hosted web survey app** that shares the existing **FastAPI** service and **SQLite medical DB** (from the medical‑report pipeline). The healthcare **agent only displays the survey URL and checks completion status**—no agentic orchestration inside the survey itself.

Each survey is addressable via URL parameters `user_id` and `survey_id` (a short code), fetches the full schema at load, renders **one question per screen**, supports **conditional branching**, persists progress, and exposes completion/status APIs for the agent and portal.

---

## 1. Scope
**In-scope**

- SPA survey web UI hosted separately from chat app
- FastAPI endpoints for survey catalog, sessions, answers, completion
- SQLite schema additions for surveys, versions, sessions, answers, and optional survey results (reusing existing `users` table)
- Conditional branching handled in the frontend
- Progress/resume via signed deep link
- Security and consent handling for PHI
- Events/analytics

**Out-of-scope**

- Payment, diagnosis, or clinical decision support
- Email/SMS provider implementation (assume existing infra)
- Admin CMS for survey authoring UI
- Any agent-driven step-by-step survey flow (agent only checks status)

---

## 2. User Experience

### 2.1 Entry via URL

- Route pattern: `/survey/:survey_id?user_id=:external_id`.
- If an **in-progress** session exists, redirect to the **next unanswered** question and show a progress bar.
- The agent and portal obtain a signed link via backend API and surface it to the user.

### 2.2 Single-Question Screens
- Show question text, help text, input control(s), and **Next**/**Back**.
- For multiselect with **exclusive options** (e.g., *None of the above*), enforce exclusivity in UI.
- Error states show field-level messages; **Next** disabled until valid.

### 2.3 Review & Submit & Submit

- Final **Review** screen by section; allow **Edit** per question.
- On submit: compute derived metrics (e.g., **BMI**) and show completion message.

### 2.4 Save/Resume

- Autosave on every valid answer.
- Signed **resume link** to the latest step; reusable from notifications.

---

## 3. Survey Model

Surveys are defined as JSON files stored in the backend (filesystem or DB). Immutable once published; new versions create a new record. Surveys belong to a **catalog** with code and type.

### 3.1 Catalog & Types
- **Codes (10 planned):** `personalization`, `heart`, `diabetes`, `hypertension`, `dietary`, `exercise`, `stress`, `sleep`, `kidney`, `liver`.
- **Display title examples:** `Heart`, `Type 2 Diabetes`, `Hypertension`, `Dietary`, `Physical Activity`, `Stress`, `Sleep`, `Kidney`, `Liver`, `Personalization`.
- **Types:** `PERSONALIZATION`, `DISEASE_RISK`, `LIFE_STYLE`.
- Mapping (initial):
  - `personalization` → `PERSONALIZATION`
  - `heart`, `diabetes`, `hypertension`, `kidney`, `liver` → `DISEASE_RISK`
  - `dietary`, `exercise`, `stress`, `sleep` → `LIFE_STYLE`

### 3.2 Core Survey Schema
```json
{
  "id": "personalization",
  "type": "PERSONALIZATION",
  "title": "Baseline Health",
  "sections": [ /* ordered arrays of questions; see 3.3 */ ],
  "branching_rules": [ /* see 3.6 */ ]
}
```

### 3.3 Question Model

Each survey contains an **ordered collection** of questions. The order is the array order inside each `sections[].questions[]`. Every question has a unique **`code`** within the survey version.

**Fields**

- `type` – one of: `INPUT`, `SINGLE_SELECT`, `MULTIPLE_SELECT`, `DROPDOWN`, `TIME`.
- `code` – stable identifier for the question (submitted with answers).
- `title` – main prompt text.
- `subtitle` – optional helper/subtitle.
- `required` – boolean.
- `unit` – expected numeric kind: `INTEGER_NUMBER` | `DECIMAL_NUMBER` (only for `INPUT`).
- `unit_text` – display unit text alongside the control (e.g., `MIN`, `mg/dL`, `mmHg`).
- `answers` – expected options for select types (see below).
- `constraints` – optional object for validation, e.g., `{ "min": 0, "max": 300, "regex": "^\d+$" }`.
- `visible_if` – optional **question-level** condition (see 3.6) evaluated along with global branching rules.
- `help` – inline help text.

**`answers` structure (for select types)**

```json
{
  "answers": [
    { "code": "never", "title": "Never" },
    { "code": "former", "title": "I quit" },
    { "code": "current", "title": "Currently" }
  ],
  "exclusiveOptions": ["none_above"] ,   // optional; codes that cannot be combined
  "allow_other": false                     // optional; if true, include free-text 'Other'
}
```

**Example question definitions**

```json
{ "type":"INPUT", "code":"height_cm", "title":"Height", "unit":"INTEGER_NUMBER", "unit_text":"cm", "required":true, "constraints": {"min":80, "max":250} }
{ "type":"SINGLE_SELECT", "code":"smoke", "title":"Do you smoke?", "required":true,
  "answers": {"answers":[{"code":"current","title":"Yes, I currently smoke"},{"code":"quit","title":"No, I quit"},{"code":"never","title":"No, I don't"}]}}
{ "type":"MULTIPLE_SELECT", "code":"conditions", "title":"I have...",
  "answers": {"answers":[{"code":"diabetes","title":"Diabetes"},{"code":"none","title":"None of the above"}], "exclusiveOptions":["none"]} }
{ "type":"TIME", "code":"sleep_minutes", "title":"How long do you sleep?", "unit_text":"MIN", "unit":"INTEGER_NUMBER", "constraints": {"min":0, "max":1440} }
```

### 3.4 Value Shapes

- `INPUT` → number (int/decimal per `unit`).
- `SINGLE_SELECT`/`DROPDOWN` → string `answer.code`.
- `MULTIPLE_SELECT` → array of `answer.code` (enforce `exclusiveOptions`).
- `TIME` → integer minutes (`unit_text: MIN`).code`.

### 3.5 Ordering & Conditional Display

- The **display order** is defined by the array order of `sections[].questions[]`.
- **Not all questions are shown**: visibility is controlled by `visible_if` (question-level) and global **branching rules** (3.6). 
- Hidden questions are skipped and any stored answers for them are **voided** when they become hidden due to answer changes.

### 3.6 Branching Semantics

- **Rule language**: declarative JSON with operators: `equals`, `one_of`, `includes`, `gt/gte/lt/lte`, `and/or/not`.
- **Actions**: `skip_questions`, `goto_question`, `insert_questions_after`, `require_questions`.
- **Evaluation**: Rules are evaluated **after each answer save** against the current answer map. The backend returns the **next question id**; the client navigates accordingly.
- **Backtracking**: If a prior answer changes and invalidates dependent answers, the backend marks those as **void** and removes them from progress.

---

## 4. Data Model (SQLite additions)
Reuses existing `users` table from the medical system. New tables / changes:

```sql
CREATE TABLE surveys (
  id TEXT PRIMARY KEY,                 -- stable internal id, e.g., 'heart', 'personalization'
  code TEXT NOT NULL UNIQUE,           -- short code used in URLs
  title TEXT NOT NULL,                 -- display name
  version TEXT NOT NULL,               -- version of the survey
  type TEXT NOT NULL CHECK (type IN ('PERSONALIZATION','DISEASE_RISK','LIFE_STYLE')),
  description TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE survey_sessions (
  id TEXT PRIMARY KEY,                 -- uuid
  survey_id INTEGER NOT NULL REFERENCES surveys(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  status TEXT NOT NULL CHECK (status IN ('in_progress','completed','cancelled','expired')),
  last_question_id TEXT,
  progress_pct INTEGER NOT NULL DEFAULT 0,
  consented_policy_version TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME
);

CREATE TABLE survey_answers (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES survey_sessions(id),
  question_id TEXT NOT NULL,
  section_id TEXT,
  value_json TEXT NOT NULL,
  voided BOOLEAN NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE survey_results (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES survey_sessions(id),
  result_json TEXT NOT NULL,           -- optional computed assessment output (e.g., risk score)
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes**
- `survey_sessions (user_id, status)`
- `survey_answers (session_id, question_id)`
- `surveys (code, type)`

---

## 5. API Design (FastAPI)
*All requests/responses are JSON; errors use `{ "ok": false, "error": {"code":"...","message":"...","details":{}} }`. All endpoints are prefixed with **`/api`**.*

### 5.1 Survey catalog & schema
- `POST /api/survey` → (create catalog entry)
- `GET /api/survey` → list of `{id, code, title, type, active_version}`
- `GET /api/survey/{code}` → full survey JSON

### 5.2 Survey response (backend is storage; branching handled in frontend)
- `POST /api/survey-response?user_id={external_id}&survey_code={code}` → sets status `completed` and optionally writes `survey_results`.
  - If an `in_progress` response exists for `(user_id, survey_code)`, overwrites it.
- `GET /api/survey-response?user_id={external_id}&survey_code={code}` → `{ ok, status, progress_pct, last_question_id, answers: array of {question_id, title, value} }`
- `POST /api/survey-response/answer?user_id={external_id}&survey_code={code}` with body `{ question_id, value }` → `{ ok, progress_pct }`

---

## 6. Frontend (SPA) Requirements
### 6.1 Overview
- Tech: Next.js + TypeScript + Tailwind
- Components: `QuestionRenderer`, `MultiSelectChips`, `RadioList`, `BooleanSwitch`, `InputWithUnit`, `ProgressBar`.
- State: SPA holds the survey schema and computes navigation; persists answers via APIs in §5.2.
- Host at `/app` or separate domain;

### 6.2. Branching Logic
- The frontend evaluates `visible_if` and `branching_rules` locally to determine the next question.
- The backend does **not** compute navigation; it only persists answers and exposes session state.
- When the frontend hides questions due to branching, it must call `POST /api/survey-sessions/{id}/void` with the affected `question_ids` so the backend drops them from progress.

---

## 7. Interop with Agno Agent
- The agent:
  - Calls `POST /api/survey-links` to obtain a signed URL.
  - Checks completion via `GET /api/survey-response?user_id={external_id}&survey_code={code}`.
- **No agentic orchestration during the survey.**
