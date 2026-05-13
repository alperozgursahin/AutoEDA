import pandas as pd

from app.services.detection.missing_rules import detect_missing_values
from app.services.detection.validity_rules import detect_type_mismatches
from app.services.suggestion_service import build_suggestions_from_issues


EXPECTED_TYPES = {
    "ID": "numeric",
    "Age": "numeric",
    "Salary": "numeric"
}


def infer_data_type(series):
    non_null = series.dropna()

    if len(non_null) == 0:
        return "unknown"

    unique_values = set(str(v).lower() for v in non_null.unique())

    if unique_values.issubset({"true", "false"}):
        return "categorical"

    numeric_series = pd.to_numeric(non_null, errors="coerce")

    numeric_ratio = numeric_series.notna().sum() / len(non_null)

    if numeric_ratio > 0.8:
        return "numeric"

    return "categorical"


def build_column_profiles(df):
    columns = []

    for column_name in df.columns:
        missing_count = int(df[column_name].isna().sum())
        data_type = EXPECTED_TYPES.get(column_name, infer_data_type(df[column_name]))

        columns.append({
            "column_name": column_name,
            "data_type": data_type,
            "missing_count": missing_count
        })

    return columns


def build_validity_profiles(df):
    columns = []

    for column_name in df.columns:
        data_type = EXPECTED_TYPES.get(
            column_name,
            infer_data_type(df[column_name])
        )

        invalid_count = 0

        if data_type == "numeric":
            non_null = df[column_name].dropna()

            numeric_series = pd.to_numeric(
                non_null,
                errors="coerce"
            )

            invalid_count = int(
                numeric_series.isna().sum()
            )

        columns.append({
            "column_name": column_name,
            "expected_type": data_type,
            "invalid_count": invalid_count
        })

    return columns


# CSV yükle
df = pd.read_csv("test.csv")

row_count = len(df)

# Profiling
missing_columns = build_column_profiles(df)
validity_columns = build_validity_profiles(df)

# Detection
missing_issues = detect_missing_values(
    missing_columns,
    row_count
)

type_mismatch_issues = detect_type_mismatches(
    validity_columns,
    row_count
)

# Merge all issues
all_issues = (
    missing_issues +
    type_mismatch_issues
)

# Build frontend-ready suggestions
suggestions = build_suggestions_from_issues(
    all_issues
)

print("\nFINAL FRONTEND-READY SUGGESTIONS:\n")

for suggestion in suggestions:
    print(suggestion)
    print()