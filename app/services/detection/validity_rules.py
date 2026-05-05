"""
Purpose:
Detect type mismatch and invalid value issues from profiling statistics.
This file does not clean data.
This file does not call LLM.
This file only returns rule-based issue objects.
"""


def detect_type_mismatches(columns: list, row_count: int) -> list:
    """
    Iterates over all columns and detects type mismatch issues.

    Args:
        columns: list of column validity profiling dictionaries
        row_count: total number of rows in dataset

    Returns:
        List of issue dictionaries
    """
    issues = []

    for col in columns:
        issue = evaluate_type_mismatch_column(col, row_count)
        if issue:
            issues.append(issue)

    return issues


def evaluate_type_mismatch_column(column: dict, row_count: int) -> dict | None:
    """
    Evaluates a single column for type mismatch issues.

    Args:
        column: column validity profiling data
        row_count: total dataset rows

    Returns:
        Issue dictionary or None
    """
    column_name = column.get("column_name")
    expected_type = column.get("expected_type", "unknown")
    invalid_count = column.get("invalid_count", 0)

    if row_count == 0:
        return None

    invalid_ratio = invalid_count / row_count

    if invalid_ratio == 0:
        return None

    if invalid_ratio <= 0.02:
        severity = "low"
        reason_code = "TM_LOW_INVALID_RATIO"
    elif invalid_ratio <= 0.10:
        severity = "medium"
        reason_code = "TM_MEDIUM_INVALID_RATIO"
    else:
        severity = "high"
        reason_code = "TM_HIGH_INVALID_RATIO"

    suggested_action = "review_column"

    return {
        "issue_id": f"type_mismatch_{column_name}",
        "column": column_name,
        "issue_type": "type_mismatch",
        "severity": severity,
        "suggested_action": suggested_action,
        "reason_code": reason_code,
        "metrics": {
            "invalid_count": invalid_count,
            "invalid_ratio": round(invalid_ratio, 4),
            "row_count": row_count,
            "expected_type": expected_type
        },
        "requires_user_approval": True
    }