import pandas as pd

from app.services.detection.missing_rules import detect_missing_values


def infer_data_type(series):
    # Boşları temizle
    non_null = series.dropna()

    # Eğer tamamen boşsa
    if len(non_null) == 0:
        return "unknown"

    # Boolean kontrol (true/false gibi)
    unique_values = set(str(v).lower() for v in non_null.unique())

    if unique_values.issubset({"true", "false"}):
        return "categorical"

    # Numeric kontrol (oran bazlı)
    numeric_series = pd.to_numeric(non_null, errors="coerce")

    numeric_ratio = numeric_series.notna().sum() / len(non_null)

    if numeric_ratio > 0.8:
        return "numeric"

    return "categorical"


def build_column_profiles(df):
    columns = []

    for column_name in df.columns:
        missing_count = int(df[column_name].isna().sum())
        data_type = infer_data_type(df[column_name])

        columns.append({
            "column_name": column_name,
            "data_type": data_type,
            "missing_count": missing_count
        })

    return columns


df = pd.read_csv("complex_test.csv")

row_count = len(df)
columns = build_column_profiles(df)

issues = detect_missing_values(columns, row_count)

print("Row count:", row_count)
print("Detected issues:")
for issue in issues:
    print(issue)