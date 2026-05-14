"""
Orchestrates all detection rules across the full pipeline.
Accepts a raw DataFrame and returns a unified list of issue dicts
compatible with suggestion_service.build_suggestions_from_issues().
"""

import pandas as pd
from typing import Optional

from app.services.detection.contracts import DetectionSuggestion
from app.services.detection.missing_rules import detect_missing_values
from app.services.detection.validity_rules import detect_type_mismatches
from app.services.detection.structural_rules import (
    detect_duplicate_rows,
    detect_constant_columns,
    detect_all_null_columns,
    detect_high_cardinality_columns,
    detect_mixed_type_columns,
)
from app.services.detection.statistical_rules import (
    detect_outliers_iqr,
    detect_skewed_distributions,
    detect_low_variance_columns,
    detect_high_correlation_pairs,
)

_STRUCTURAL_STATISTICAL_RULES = [
    detect_duplicate_rows,
    detect_constant_columns,
    detect_all_null_columns,
    detect_high_cardinality_columns,
    detect_mixed_type_columns,
    detect_outliers_iqr,
    detect_skewed_distributions,
    detect_low_variance_columns,
    detect_high_correlation_pairs,
]


def run_all_rules(
    df: pd.DataFrame,
    expected_types: Optional[dict] = None,
) -> list:
    """
    Runs all detection rules on a DataFrame.

    Args:
        df: The raw dataset to analyze. Never mutated.
        expected_types: Optional {column_name: "numeric"|"categorical"} mapping.
                        When provided, Doğa's type-mismatch rules are also run.
                        Without it, structural mixed-type detection already covers
                        type inconsistencies from the DataFrame directly.

    Returns:
        Unified list of issue dicts compatible with
        suggestion_service.build_suggestions_from_issues().
    """
    row_count = len(df)
    issues: list = []

    # ── Doğa's rule layer (profiling-dict based) ──────────────────────────────
    missing_profiles = _build_missing_profiles(df)
    issues.extend(detect_missing_values(missing_profiles, row_count))

    if expected_types:
        validity_profiles = _build_validity_profiles(df, expected_types)
        issues.extend(detect_type_mismatches(validity_profiles, row_count))

    # ── Benhur's rule layer (DataFrame based) ─────────────────────────────────
    our_suggestions: list[DetectionSuggestion] = []
    for rule_fn in _STRUCTURAL_STATISTICAL_RULES:
        our_suggestions.extend(rule_fn(df))

    offset = len(issues)
    for i, suggestion in enumerate(our_suggestions, start=1):
        issues.append(_suggestion_to_issue_dict(suggestion, offset + i))

    return issues


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_missing_profiles(df: pd.DataFrame) -> list:
    """Derives column-level missing value profiling dicts directly from a DataFrame."""
    profiles = []
    for col in df.columns:
        data_type = "numeric" if pd.api.types.is_numeric_dtype(df[col]) else "categorical"
        profiles.append({
            "column_name": col,
            "missing_count": int(df[col].isna().sum()),
            "data_type": data_type,
        })
    return profiles


def _build_validity_profiles(df: pd.DataFrame, expected_types: dict) -> list:
    """
    Builds column-level validity profiling dicts using caller-supplied expected types.
    Only produces a profile for a column when invalid values are actually found.
    """
    profiles = []
    for col, expected_type in expected_types.items():
        if col not in df.columns:
            continue
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        if expected_type == "numeric":
            invalid_count = int(pd.to_numeric(non_null, errors="coerce").isna().sum())
        else:
            invalid_count = 0
        if invalid_count > 0:
            profiles.append({
                "column_name": col,
                "expected_type": expected_type,
                "invalid_count": invalid_count,
            })
    return profiles


def _suggestion_to_issue_dict(s: DetectionSuggestion, index: int) -> dict:
    """
    Converts a DetectionSuggestion Pydantic object into the unified issue dict
    format that suggestion_service.build_suggestions_from_issues() expects.
    """
    col_key = (s.column or "dataset").replace(" ", "_")
    return {
        "issue_id": f"{s.issue_type.lower()}_{col_key}_{index}",
        "column": s.column,
        "issue_type": s.issue_type,
        "severity": s.severity,
        "suggested_action": s.suggested_action,
        "reason_code": s.issue_type,
        "metrics": s.action_params or {},
        "description": s.description,
        "requires_user_approval": True,
    }
