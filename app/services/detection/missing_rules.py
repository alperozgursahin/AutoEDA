"""
Purpose:
Detect missing value issues from profiling statistics.
This file does not clean data.
This file does not call LLM.
This file only returns rule-based issue objects.
"""

def detect_missing_values(columns: list, row_count: int) -> list:
    """
    Iterates over all columns and detects missing value issues.

    Args:
        columns: list of column profiling dictionaries
        row_count: total number of rows in dataset

    Returns:
        List of issue dictionaries
    """
    issues = []

    for col in columns:
        issue = evaluate_missing_column(col, row_count)
        if issue:
            issues.append(issue)

    return issues

def evaluate_missing_column(column: dict, row_count: int) -> dict | None: # rule engine
    """
    Evaluates a single column for missing values.

    Args:
        column: column profiling data
        row_count: total dataset rows

    Returns:
        Issue dictionary or None
    """
    missing_count = column.get("missing_count", 0)

    if row_count == 0:
        return None

    missing_ratio = missing_count / row_count

    column_name = column.get("column_name")
    data_type = column.get("data_type", "unknown")

    if missing_ratio == 0:
        return None

    if missing_ratio <= 0.05:
        severity = "low"
        if data_type == "numeric":
            suggested_action = "fill_mean"
            reason_code = "MV_LOW_NUMERIC"
        elif data_type == "categorical":
            suggested_action = "fill_mode"
            reason_code = "MV_LOW_CATEGORICAL"
        else:
            suggested_action = "review_column"
            reason_code = "MV_LOW_UNKNOWN_TYPE"

    elif missing_ratio <= 0.30:
        severity = "medium"
        if data_type == "numeric":
            suggested_action = "fill_median"
            reason_code = "MV_MEDIUM_NUMERIC"
        elif data_type == "categorical":
            suggested_action = "fill_mode"
            reason_code = "MV_MEDIUM_CATEGORICAL"
        else:
            suggested_action = "review_column"
            reason_code = "MV_MEDIUM_UNKNOWN_TYPE"

    elif missing_ratio <= 0.60:
        severity = "high"
        suggested_action = "review_column"
        reason_code = "MV_HIGH_RATIO"

    else:
        severity = "critical"
        suggested_action = "drop_column"
        reason_code = "MV_CRITICAL_RATIO"

    return {
        "issue_id": f"missing_values_{column_name}",
        "column": column_name,
        "issue_type": "missing_values",
        "severity": severity,
        "suggested_action": suggested_action,
        "reason_code": reason_code,
        "metrics": {
            "missing_count": missing_count,
            "missing_ratio": round(missing_ratio, 4),
            "row_count": row_count
        },
        "requires_user_approval": True
    }
