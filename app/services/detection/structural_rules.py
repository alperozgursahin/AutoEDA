import pandas as pd
from typing import List
from app.services.detection.contracts import DetectionSuggestion

_HIGH_CARDINALITY_THRESHOLD = 0.9
_MIN_ROWS_FOR_CARDINALITY = 50


def detect_duplicate_rows(df: pd.DataFrame) -> List[DetectionSuggestion]:
    n_duplicates = int(df.duplicated().sum())
    if n_duplicates == 0:
        return []
    ratio = n_duplicates / len(df)
    return [DetectionSuggestion(
        column=None,
        issue_type="DUPLICATE_ROWS",
        description=(
            f"{n_duplicates} duplicate row(s) detected "
            f"({ratio:.1%} of the dataset). These are exact copies of other rows "
            "and add no analytical value."
        ),
        suggested_action="drop_duplicates",
        requires_user_approval=True,
        severity="high" if ratio > 0.1 else "medium",
    )]


def detect_constant_columns(df: pd.DataFrame) -> List[DetectionSuggestion]:
    suggestions = []
    for col in df.columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        if non_null.nunique() == 1:
            suggestions.append(DetectionSuggestion(
                column=col,
                issue_type="CONSTANT_COLUMN",
                description=(
                    f"Column '{col}' has only one unique non-null value "
                    f"('{non_null.iloc[0]}'). It provides no discriminating "
                    "information for analysis."
                ),
                suggested_action="drop_column",
                requires_user_approval=True,
                severity="medium",
            ))
    return suggestions


def detect_all_null_columns(df: pd.DataFrame) -> List[DetectionSuggestion]:
    suggestions = []
    for col in df.columns:
        if df[col].isna().all():
            suggestions.append(DetectionSuggestion(
                column=col,
                issue_type="ALL_NULL_COLUMN",
                description=(
                    f"Column '{col}' contains no values — every row is null. "
                    "The column carries no information and cannot be used in analysis."
                ),
                suggested_action="drop_column",
                requires_user_approval=True,
                severity="high",
            ))
    return suggestions


def detect_high_cardinality_columns(df: pd.DataFrame) -> List[DetectionSuggestion]:
    if len(df) < _MIN_ROWS_FOR_CARDINALITY:
        return []
    suggestions = []
    # include="string" catches pandas 3.x StringDtype; "object" catches older pandas
    for col in df.select_dtypes(include=["object", "string"]).columns:
        n_unique = df[col].nunique(dropna=True)
        ratio = n_unique / len(df)
        if ratio > _HIGH_CARDINALITY_THRESHOLD:
            suggestions.append(DetectionSuggestion(
                column=col,
                issue_type="HIGH_CARDINALITY",
                description=(
                    f"Column '{col}' has {n_unique} unique values out of {len(df)} rows "
                    f"({ratio:.1%} unique). This is likely an identifier or free-text field "
                    "that will not generalize in statistical analysis."
                ),
                suggested_action="drop_column",
                requires_user_approval=True,
                severity="low",
            ))
    return suggestions


def detect_mixed_type_columns(df: pd.DataFrame) -> List[DetectionSuggestion]:
    suggestions = []
    for col in df.select_dtypes(include=["object", "string"]).columns:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        numeric_count = int(pd.to_numeric(non_null, errors="coerce").notna().sum())
        string_count = len(non_null) - numeric_count
        if 0 < numeric_count < len(non_null) and string_count > 0:
            suggestions.append(DetectionSuggestion(
                column=col,
                issue_type="MIXED_TYPES",
                description=(
                    f"Column '{col}' contains a mix of numeric ({numeric_count}) and "
                    f"non-numeric ({string_count}) values. This suggests data entry errors "
                    "or a formatting inconsistency that will cause coercion failures."
                ),
                suggested_action="drop_column",
                requires_user_approval=True,
                severity="medium",
            ))
    return suggestions
