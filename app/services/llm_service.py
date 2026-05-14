"""
Purpose:
Generate plain-English explanations for rule-based data quality issues.
This file does not decide cleaning actions.
This file does not modify data.
The rule engine decides severity and suggested_action.
"""


def generate_fallback_explanation(issue: dict) -> dict:
    """
    Generates a safe fallback explanation when the LLM is not available.

    Args:
        issue: rule-based issue dictionary

    Returns:
        Explanation dictionary with user-facing messages
    """

    column = issue.get("column", "this column")
    issue_type = issue.get("issue_type", "data_quality_issue")
    severity = issue.get("severity", "medium")
    suggested_action = issue.get("suggested_action", "review_column")
    metrics = issue.get("metrics", {})

    # Missing Values Explanation
    if issue_type == "missing_values":

        missing_count = metrics.get("missing_count", 0)
        missing_ratio = metrics.get("missing_ratio", 0)
        missing_percentage = round(missing_ratio * 100, 2)

        return {
            "explanation": (
                f"The column '{column}' contains {missing_count} missing values, "
                f"which represents {missing_percentage}% of the dataset."
            ),

            "recommendation_reason": (
                f"The system classified this as a {severity} issue and suggested "
                f"'{suggested_action}' based on the missing value ratio."
            ),

            "user_warning": (
                "Please review this suggestion before approving it. "
                "The original dataset will not be modified unless you approve the action."
            )
        }

    # Type Mismatch Explanation
    if issue_type == "type_mismatch":

        invalid_count = metrics.get("invalid_count", 0)
        invalid_ratio = metrics.get("invalid_ratio", 0)
        expected_type = metrics.get("expected_type", "expected type")

        invalid_percentage = round(invalid_ratio * 100, 2)

        return {
            "explanation": (
                f"The column '{column}' contains {invalid_count} invalid values "
                f"({invalid_percentage}% of the dataset) that do not match the expected "
                f"{expected_type} type."
            ),

            "recommendation_reason": (
                f"The system classified this as a {severity} issue and suggested "
                f"'{suggested_action}' because inconsistent values may reduce data reliability."
            ),

            "user_warning": (
                "Please inspect the invalid values before approving any cleaning action."
            )
        }

    # ── Benhur's structural & statistical issue types ────────────────────────
    # For these types the rule engine already produces a user-friendly description.
    # We reuse it as the explanation and add issue-specific reasoning / warnings.

    if issue_type == "DUPLICATE_ROWS":
        return {
            "explanation": issue.get("description", f"Duplicate rows were detected in the dataset."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Duplicate rows inflate statistics, distort frequency counts, "
                "and can cause data leakage in model training."
            ),
            "user_warning": (
                "Dropping duplicates is irreversible. "
                "Verify the flagged rows are true duplicates and not legitimate repeated observations."
            ),
        }

    if issue_type == "CONSTANT_COLUMN":
        return {
            "explanation": issue.get("description", f"Column '{column}' has only one unique value."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Columns with zero variance carry no information and add unnecessary noise to analysis."
            ),
            "user_warning": (
                "Verify this column is not intentionally constant "
                "(e.g., a version flag or dataset-level metadata) before dropping it."
            ),
        }

    if issue_type == "ALL_NULL_COLUMN":
        return {
            "explanation": issue.get("description", f"Column '{column}' contains no values at all."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "A completely empty column cannot contribute to any analysis or model."
            ),
            "user_warning": (
                "Ensure this column is not expected to be populated by a future data pipeline "
                "before approving the drop."
            ),
        }

    if issue_type == "HIGH_CARDINALITY":
        return {
            "explanation": issue.get("description", f"Column '{column}' has very high cardinality."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "High-cardinality string columns (IDs, free text) cannot be used directly "
                "in most statistical analyses or machine learning models."
            ),
            "user_warning": (
                "Confirm this is not a meaningful low-cardinality column "
                "before dropping it — check whether the unique count is expected."
            ),
        }

    if issue_type == "MIXED_TYPES":
        return {
            "explanation": issue.get("description", f"Column '{column}' contains mixed data types."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Mixed-type columns cause silent coercion errors in numeric operations "
                "and unreliable aggregations."
            ),
            "user_warning": (
                "Inspect the non-numeric values before approving — "
                "they may represent valid categories or data entry errors that need manual correction."
            ),
        }

    if issue_type == "OUTLIERS_IQR":
        metrics_str = ""
        lower = metrics.get("lower_bound")
        upper = metrics.get("upper_bound")
        if lower is not None and upper is not None:
            metrics_str = f" Proposed clip range: [{lower:.4g}, {upper:.4g}]."
        return {
            "explanation": issue.get("description", f"Column '{column}' contains outliers detected by IQR."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Outliers distort means, inflate variance, and can destabilize model training."
                f"{metrics_str}"
            ),
            "user_warning": (
                "Review the proposed clip bounds — they are derived from quartiles "
                "and may need adjustment for your specific domain."
            ),
        }

    if issue_type == "SKEWED_DISTRIBUTION":
        return {
            "explanation": issue.get("description", f"Column '{column}' has a heavily skewed distribution."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Heavy skew biases mean-based statistics and can degrade gradient-based model performance."
            ),
            "user_warning": (
                "Clipping reduces the tail effect but does not eliminate skew. "
                "Consider a log or square-root transformation as an alternative."
            ),
        }

    if issue_type == "LOW_VARIANCE":
        return {
            "explanation": issue.get("description", f"Column '{column}' has very low variance."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Near-constant numeric columns provide minimal discriminating signal "
                "for statistical analysis or model training."
            ),
            "user_warning": (
                "Verify the column is not a deliberately scaled or normalized feature "
                "before approving the drop."
            ),
        }

    if issue_type == "HIGH_CORRELATION":
        return {
            "explanation": issue.get("description", f"Column '{column}' is highly correlated with another column."),
            "recommendation_reason": (
                f"The system classified this as a {severity} issue. "
                "Highly correlated columns introduce multicollinearity, "
                "inflating model variance and making coefficient interpretation unreliable."
            ),
            "user_warning": (
                "Dropping a column is permanent. Confirm which of the correlated pair "
                "is more meaningful to retain before approving."
            ),
        }

    # Generic Fallback
    return {
        "explanation": (
            f"The column '{column}' has a detected data quality issue."
        ),

        "recommendation_reason": (
            f"The system classified this as a {severity} issue and suggested "
            f"'{suggested_action}' based on rule-based analysis."
        ),

        "user_warning": (
            "Please review this suggestion before approving it."
        )
    }

