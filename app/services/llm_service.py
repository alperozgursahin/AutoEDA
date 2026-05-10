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

