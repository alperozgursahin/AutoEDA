from app.services.llm_service import generate_fallback_explanation


missing_issue = {
    "column": "Age",
    "issue_type": "missing_values",
    "severity": "critical",
    "suggested_action": "drop_column",
    "metrics": {
        "missing_count": 62,
        "missing_ratio": 0.62,
        "row_count": 100
    }
}

type_mismatch_issue = {
    "column": "Salary",
    "issue_type": "type_mismatch",
    "severity": "medium",
    "suggested_action": "review_column",
    "metrics": {
        "invalid_count": 5,
        "invalid_ratio": 0.05,
        "row_count": 100,
        "expected_type": "numeric"
    }
}


print("Missing Values Explanation:")
print(generate_fallback_explanation(missing_issue))

print("\nType Mismatch Explanation:")
print(generate_fallback_explanation(type_mismatch_issue))