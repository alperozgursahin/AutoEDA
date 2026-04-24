# AutoEDA: Intelligent Data Quality Analyzer - Master Project Memory

## 1. Project Context & Mission
This is a high-stakes Senior Software Engineering Capstone Project at Izmir University of Economics.
**Objective:** Develop a web-based platform that automates the early stages of the data science pipeline (Ingestion, Profiling, Analysis, and Cleaning) while maintaining explainability and user control.

### Core Principles
- **Explainability (XAI):** Every detected issue and suggested cleaning step must be explained in plain English (LLM-supported).
- **Human-in-the-Loop:** No destructive data changes (dropping columns, filling nulls) are allowed without explicit user confirmation.
- **Data Integrity:** The original dataset is read-only. Transformations are applied to a copy, and a versioned "Cleaned Dataset" is generated.
- **Asynchronous Reliability:** Heavy computations (profiling/cleaning) must not block the API.

## 2. Technology Stack & Environment
- **Runtime:** Python 3.11+
- **Framework:** FastAPI (Asynchronous routes)
- **Data Processing:** Pandas, NumPy, Scikit-learn (Statistical analysis & cleaning)
- **Database:** PostgreSQL (with JSONB for flexible logging and stats)
- **Async Workflow:** Celery + Redis (Task queue management)
- **Frontend:** React (State-managed interactive UI)
- **Security:** Password hashing (bcrypt/Argon2), JWT authentication
- **Constraints:** Max file size 50MB; support for CSV and XLSX formats.

## 3. Modular Architecture (Strict adherence required)
All backend code must be organized within the following modular structure:

- `app/api/`: Routing and request handling.
- `app/models/`: SQLAlchemy ORM models (refer to the Database Schema).
- `app/schemas/`: Pydantic models for request/response validation.
- `app/services/`: 
    - `ingestion.py`: File validation, reading into DataFrames, size checks.
    - `profiling.py`: Calculating dataset/column-level stats (mean, median, missing ratios).
    - `analyzer.py`: Rule-based detection (IQR for outliers, Duplicate detection).
    - `suggestion_engine.py`: Logic for mapping detected issues to specific cleaning actions.
    - `execution.py`: Atomic application of approved transformations.
    - `reporting.py`: Generation of PDF/HTML reports with "Before vs After" metrics.
- `app/worker.py`: Background task definitions for Celery.

## 4. Final Database Schema (Source of Truth)
Ensure all DB interactions align with this refined structure:

```mermaid
erDiagram
    USERS {
        uuid id PK
        varchar full_name
        varchar email UK
        varchar password_hash
        boolean is_active
        timestamp created_at
    }
    DATASETS {
        uuid id PK
        uuid user_id FK
        varchar original_filename
        varchar file_path "Path to raw CSV/XLSX"
        varchar cleaned_file_path "Path to versioned clean data"
        varchar report_file_path "Path to PDF/HTML report"
        integer file_size_bytes
        boolean is_deleted "Soft delete"
        varchar status "UPLOADED, PROFILING, AWAITING_APPROVAL, CLEANING, DONE, FAILED"
        timestamp uploaded_at
    }
    PROFILING_RESULTS {
        uuid id PK
        uuid dataset_id FK
        float pre_cleaning_score "Initial health score (0-100)"
        float post_cleaning_score "Score after approved transformations"
        jsonb dataset_statistics "Metadata: row/col counts, global missing ratio"
        jsonb column_statistics "Per-column: type, unique counts, outliers"
        jsonb detected_issues "Diagnostic log of anomalies found"
        timestamp created_at
    }
    CLEANING_SUGGESTIONS_LOGS {
        uuid id PK
        uuid dataset_id FK
        varchar action_type "DROP_COLUMN, FILL_MEDIAN, REMOVE_DUPLICATES, etc."
        varchar target_column
        text explanation "LLM/Rule justification for the user"
        varchar suggestion_status "SUGGESTED, APPROVED, REJECTED, EXECUTED, FAILED"
        timestamp applied_at
    }
    USERS ||--o{ DATASETS : "uploads"
    DATASETS ||--|| PROFILING_RESULTS : "analyzed_by"
    DATASETS ||--o{ CLEANING_SUGGESTIONS_LOGS : "history"