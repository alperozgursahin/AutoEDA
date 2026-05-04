# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoEDA is a web platform for intelligent data quality analysis and automated data cleaning, built as a Senior Capstone Project (FENG 498) at Izmir University of Economics. The core philosophy is **Human-in-the-Loop**: every cleaning action requires explicit user approval before execution, and original datasets are never mutated.

## Development Commands

### Infrastructure
```bash
# Start PostgreSQL (port 5433) and Redis (port 6379)
docker-compose up -d
```

### Backend API
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server (dev)
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.core.celery_app worker --loglevel=info
```

### Database Migrations
```bash
# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

### API Documentation
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Architecture

### Request Lifecycle
1. Client sends `POST /{dataset_id}/execute` with a list of **approved** `ActionItem` objects
2. FastAPI handler returns `202 ACCEPTED` with a `task_id` immediately
3. `execute_cleaning_task` Celery job picks up the work asynchronously
4. Worker calls `apply_cleaning()` (execution.py) then `generate_report()` (reporting.py)
5. Client polls Celery result backend (Redis) for task completion and downloads the HTML report via `GET /reports/{report_name}`

### Module Responsibilities
- **app/api/**: HTTP layer only — no business logic. Routes delegate directly to services or Celery tasks.
- **app/services/**: Pure business logic (no FastAPI/Celery imports). `execution.py` applies pandas transformations; `reporting.py` generates HTML.
- **app/worker/tasks.py**: Thin Celery task wrappers that call services.
- **app/models/**: SQLAlchemy ORM with async support (asyncpg). All PKs are UUIDs.
- **app/schemas/**: Pydantic v2 models for request/response validation, separate from ORM models.
- **app/core/**: Config, DB engine, and Celery app initialization.

### Dataset Status Flow
`UPLOADED → PROFILING → AWAITING_APPROVAL → CLEANING → DONE / FAILED`

Transitions are managed by updating `datasets.status`. The `CleaningSuggestionsLog` table tracks individual action states: `SUGGESTED → APPROVED/REJECTED → EXECUTED/FAILED`.

### Supported Cleaning Actions
Actions are string identifiers passed in `ActionItem.action`:
- `drop_duplicates` — no column required
- `drop_column` — requires `column`
- `fill_median` / `fill_mean` — numeric columns only, requires `column`
- `drop_missing_rows` — requires `column`

New actions must be added to the `apply_cleaning()` dispatch in [app/services/execution.py](app/services/execution.py).

### Database Configuration
Credentials are currently hardcoded in [app/core/config.py](app/core/config.py):
- PostgreSQL: `postgresql+asyncpg://autoeda_user:autoeda_password@localhost:5433/autoeda`
- Redis: `redis://localhost:6379/0`

The Alembic env ([alembic/env.py](alembic/env.py)) imports all models via `app/models/__init__.py` for autogenerate to work — always export new models from that file.

## What Is Not Yet Implemented

The following services are architectural placeholders not yet built:

## Detection & Suggestion Module Work Split

This section defines the team ownership for the rule-based detection and LLM-backed suggestion generation module.

The detection layer must never mutate the original dataset. It only detects data quality issues and generates suggestion objects. Cleaning is executed later only after explicit user approval through the existing async execution flow.

### Shared Detection Principles

All detection rules must follow these principles:

- Detection rules must be deterministic and rule-based.
- Detection rules must not directly clean, modify, or overwrite datasets.
- Detection rules must not call Celery directly.
- Detection rules must not call FastAPI route handlers.
- Detection rules should return structured issue/suggestion objects.
- Every suggestion must include `requires_user_approval: true`.
- The LLM must not decide the cleaning action. The rule engine decides the action; the LLM only explains it in plain English.
- Original uploaded files must always remain unchanged.
- Rules should work with mock profiling data until the profiling pipeline is fully implemented.

### Suggested Directory Structure

Use a separated rule-file structure to avoid merge conflicts between team members:

```text
app/services/detection/
├── missing_rules.py          # Doğa
├── validity_rules.py         # Doğa
├── structural_rules.py       # Benhur
├── statistical_rules.py      # Benhur
├── rule_registry.py          # Shared, edit carefully
└── contracts.md              # Shared rule/output contracts
app/services/llm_service.py          # Doğa
app/services/suggestion_service.py   # Shared integration layer

- Dataset upload endpoint and file ingestion
- Data profiling trigger and `profiling_result` population
- LLM-backed suggestion generation (`explanation` field on `CleaningSuggestionsLog`)
- User authentication and authorization
- Frontend (expected as a separate React/Next.js repository)

CORS is currently set to `allow_origins=["*"]` in [app/main.py](app/main.py) — this must be restricted before any production deployment.
