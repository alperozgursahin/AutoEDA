from app.services.suggestion_service import build_suggestions_from_issues


issues = [
    {
        "issue_id": "missing_values_Age",
        "column": "Age",
        "issue_type": "missing_values",
        "severity": "critical",
        "suggested_action": "drop_column",
        "reason_code": "MV_CRITICAL_RATIO",
        "metrics": {
            "missing_count": 62,
            "missing_ratio": 0.62,
            "row_count": 100
        },
        "requires_user_approval": True
    },

    {
        "issue_id": "type_mismatch_Salary",
        "column": "Salary",
        "issue_type": "type_mismatch",
        "severity": "medium",
        "suggested_action": "review_column",
        "reason_code": "TM_MEDIUM_INVALID_RATIO",
        "metrics": {
            "invalid_count": 5,
            "invalid_ratio": 0.05,
            "row_count": 100,
            "expected_type": "numeric"
        },
        "requires_user_approval": True
    }
]


suggestions = build_suggestions_from_issues(issues)

print("Generated Suggestions:\n")

for suggestion in suggestions:
    print(suggestion)
    print()