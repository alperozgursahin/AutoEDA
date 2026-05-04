import pandas as pd
from typing import List
from app.services.detection.contracts import DetectionSuggestion

_OUTLIER_MIN_ROWS = 10
_SKEWNESS_THRESHOLD = 2.0
_LOW_VARIANCE_CV_THRESHOLD = 0.01
_HIGH_CORRELATION_THRESHOLD = 0.95


def detect_outliers_iqr(df: pd.DataFrame) -> List[DetectionSuggestion]:
    suggestions = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < _OUTLIER_MIN_ROWS:
            continue
        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        n_outliers = int(((series < lower) | (series > upper)).sum())
        if n_outliers == 0:
            continue
        ratio = n_outliers / len(series)
        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="OUTLIERS_IQR",
            description=(
                f"Column '{col}' has {n_outliers} outlier(s) ({ratio:.1%}) "
                f"outside the IQR fence [{lower:.4g}, {upper:.4g}]. "
                "These values may distort means, correlations, and model training."
            ),
            suggested_action="clip_outliers",
            action_params={"lower_bound": round(float(lower), 6), "upper_bound": round(float(upper), 6)},
            requires_user_approval=True,
            severity="high" if ratio > 0.05 else "medium",
        ))
    return suggestions


def detect_skewed_distributions(df: pd.DataFrame) -> List[DetectionSuggestion]:
    suggestions = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) < 3:
            continue
        skewness = float(series.skew())
        if abs(skewness) <= _SKEWNESS_THRESHOLD:
            continue
        direction = "right (positive)" if skewness > 0 else "left (negative)"
        # Use 1st/99th percentile as clip bounds to address the extreme tail driving skewness
        lower = round(float(series.quantile(0.01)), 6)
        upper = round(float(series.quantile(0.99)), 6)
        suggestions.append(DetectionSuggestion(
            column=col,
            issue_type="SKEWED_DISTRIBUTION",
            description=(
                f"Column '{col}' is heavily skewed {direction} (skewness={skewness:.2f}). "
                "Extreme skew biases mean-based statistics and degrades model performance. "
                "Clipping the 1st–99th percentile range can reduce the tail effect."
            ),
            suggested_action="clip_outliers",
            action_params={"lower_bound": lower, "upper_bound": upper},
            requires_user_approval=True,
            severity="high" if abs(skewness) > 5.0 else "medium",
        ))
    return suggestions


def detect_low_variance_columns(df: pd.DataFrame) -> List[DetectionSuggestion]:
    suggestions = []
    for col in df.select_dtypes(include="number").columns:
        series = df[col].dropna()
        if len(series) == 0:
            continue
        std = float(series.std())
        if std == 0:
            continue  # Already caught by structural detect_constant_columns
        mean_abs = float(series.abs().mean())
        if mean_abs == 0:
            continue
        cv = std / mean_abs
        if cv < _LOW_VARIANCE_CV_THRESHOLD:
            suggestions.append(DetectionSuggestion(
                column=col,
                issue_type="LOW_VARIANCE",
                description=(
                    f"Column '{col}' has very low variance (CV={cv:.4f}). "
                    "Values are nearly identical across all rows, providing minimal "
                    "discriminating information for analysis or modeling."
                ),
                suggested_action="drop_column",
                requires_user_approval=True,
                severity="low",
            ))
    return suggestions


def detect_high_correlation_pairs(df: pd.DataFrame) -> List[DetectionSuggestion]:
    numeric_df = df.select_dtypes(include="number")
    if numeric_df.shape[1] < 2:
        return []
    corr = numeric_df.corr().abs()
    suggestions = []
    seen = set()
    for col_a in corr.columns:
        for col_b in corr.columns:
            if col_a >= col_b:
                continue
            pair = (col_a, col_b)
            if pair in seen:
                continue
            seen.add(pair)
            corr_val = corr.loc[col_a, col_b]
            if pd.isna(corr_val) or corr_val <= _HIGH_CORRELATION_THRESHOLD:
                continue
            suggestions.append(DetectionSuggestion(
                column=col_b,
                issue_type="HIGH_CORRELATION",
                description=(
                    f"Columns '{col_a}' and '{col_b}' are highly correlated "
                    f"(r={corr_val:.3f}). Keeping both introduces multicollinearity "
                    f"in models. Consider dropping '{col_b}'."
                ),
                suggested_action="drop_column",
                requires_user_approval=True,
                severity="medium",
            ))
    return suggestions
