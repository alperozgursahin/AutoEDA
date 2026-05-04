# Detection Module — Output Contracts

All detection rule functions must return `List[DetectionSuggestion]`.  
The `DetectionSuggestion` Pydantic model is defined in `contracts.py`.

## DetectionSuggestion Fields

| Field | Type | Description |
|---|---|---|
| `column` | `str \| None` | Target column name, or `None` for dataset-level issues |
| `issue_type` | `str` | Uppercase identifier (see table below) |
| `description` | `str` | Plain-English explanation shown to the user |
| `suggested_action` | `str` | Action string matching `execution.py` dispatch keys |
| `action_params` | `dict \| None` | Extra parameters (e.g. `lower_bound`/`upper_bound` for outlier clipping) |
| `requires_user_approval` | `bool` | Always `True` — never set to `False` |
| `severity` | `"low" \| "medium" \| "high"` | Urgency level for UI display |

## Valid `suggested_action` Values

These must match the action strings handled in `app/services/execution.py`:

| Action | Notes |
|---|---|
| `drop_duplicates` | No column required |
| `drop_column` | Requires `column` |
| `fill_median` | Numeric columns only, requires `column` |
| `fill_mean` | Numeric columns only, requires `column` |
| `fill_mode` | Requires `column` |
| `drop_missing_rows` | Requires `column` |
| `clip_outliers` | Requires `column` + `action_params: {lower_bound, upper_bound}` |
| `drop_outliers` | Requires `column` + `action_params: {lower_bound, upper_bound}` |

## Known `issue_type` Values

| issue_type | Owner file |
|---|---|
| `DUPLICATE_ROWS` | structural_rules.py |
| `CONSTANT_COLUMN` | structural_rules.py |
| `ALL_NULL_COLUMN` | structural_rules.py |
| `HIGH_CARDINALITY` | structural_rules.py |
| `MIXED_TYPES` | structural_rules.py |
| `OUTLIERS_IQR` | statistical_rules.py |
| `SKEWED_DISTRIBUTION` | statistical_rules.py |
| `LOW_VARIANCE` | statistical_rules.py |
| `HIGH_CORRELATION` | statistical_rules.py |

## Invariants (All Rules Must Respect)

- Detection functions must **never mutate** the input DataFrame.
- Detection functions must **never call Celery** or any FastAPI route handler.
- Detection functions must accept `pd.DataFrame` and return `List[DetectionSuggestion]`.
- Each function must be independently testable with a mock DataFrame.
- The LLM decides nothing about the action — the rule engine does. The LLM only writes the `description` in plain English (when integrated).
