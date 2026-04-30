import pandas as pd
import numpy as np


def _safe_numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(df[column], errors="coerce").dropna()


def build_visualization_data(input_file_path: str) -> dict:
    df = pd.read_csv(input_file_path)
    numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()

    # Include numeric-looking object columns by coercion for dirty datasets.
    for column in df.columns:
        if column in numeric_columns:
            continue
        coerced = pd.to_numeric(df[column], errors="coerce")
        if coerced.notna().sum() > 0:
            numeric_columns.append(column)

    histograms = {}
    box_plots = {}
    categorical_counts = {}

    for column in numeric_columns:
        series = _safe_numeric_series(df, column)
        if series.empty:
            continue

        counts, bin_edges = np.histogram(series, bins=10)
        histogram_bins = []
        for idx, count in enumerate(counts.tolist()):
            histogram_bins.append(
                {
                    "bin_start": float(bin_edges[idx]),
                    "bin_end": float(bin_edges[idx + 1]),
                    "count": int(count),
                }
            )
        histograms[column] = histogram_bins

        q1 = float(series.quantile(0.25))
        q2 = float(series.quantile(0.5))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        outliers = series[(series < lower_fence) | (series > upper_fence)].tolist()

        box_plots[column] = {
            "min": float(series.min()),
            "q1": q1,
            "median": q2,
            "q3": q3,
            "max": float(series.max()),
            "outliers": [float(value) for value in outliers],
        }

    for column in df.columns:
        if column in numeric_columns:
            continue
        normalized = (
            df[column]
            .astype(str)
            .str.strip()
            .replace({"": np.nan, "nan": np.nan, "None": np.nan})
            .dropna()
        )
        if normalized.empty:
            continue
        counts = normalized.value_counts().head(12)
        categorical_counts[column] = [{"value": str(idx), "count": int(val)} for idx, val in counts.items()]

    numeric_frame = pd.DataFrame({column: pd.to_numeric(df[column], errors="coerce") for column in numeric_columns})
    correlation_matrix = numeric_frame.corr(numeric_only=True).fillna(0.0)

    correlations = {
        "columns": correlation_matrix.columns.tolist(),
        "matrix": correlation_matrix.round(4).values.tolist(),
    }

    return {
        "input_file_path": input_file_path,
        "row_count": int(df.shape[0]),
        "column_count": int(df.shape[1]),
        "numeric_columns": numeric_columns,
        "histograms": histograms,
        "box_plots": box_plots,
        "categorical_counts": categorical_counts,
        "correlations": correlations,
    }

