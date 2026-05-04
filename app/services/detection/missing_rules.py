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

def evaluate_missing_column(column: dict, row_count: int) -> dict | None:
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

    print(column["column_name"], missing_ratio)
    return None
